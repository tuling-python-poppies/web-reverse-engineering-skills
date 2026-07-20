#!/usr/bin/env node

const fs = require('fs')
const path = require('path')
const parser = require('@babel/parser')
const traverse = require('@babel/traverse').default
const generator = require('@babel/generator').default
const t = require('@babel/types')

function parseCode(code) {
  const ast = parser.parse(code, {
    sourceType: 'unambiguous',
    errorRecovery: true,
    plugins: ['jsx']
  })
  if (ast.errors?.length) {
    const first = ast.errors[0]
    throw new SyntaxError(`Babel recovered ${ast.errors.length} parse error(s); refusing transform: ${first.message}`)
  }
  return ast
}

function generateCode(ast) {
  return generator(ast, {
    comments: false,
    jsescOption: { minimal: true }
  }).code
}

function reparse(ast) {
  return parseCode(generateCode(ast))
}

function applyVisitors(ast, visitors) {
  for (const visitor of visitors) {
    traverse(ast, visitor)
  }
  return ast
}

function countMatches(code, regex) {
  const matches = code.match(regex)
  return matches ? matches.length : 0
}

function cloneStatements(statements) {
  return statements.map((statement) => t.cloneNode(statement, true))
}

function containsHoistedDeclaration(node, isRoot = true) {
  if (!node) return false
  if (t.isFunctionDeclaration(node) || t.isVariableDeclaration(node, { kind: 'var' })) return true
  if (!isRoot && t.isFunction(node)) return false
  const keys = t.VISITOR_KEYS[node.type] || []
  return keys.some((key) => {
    const child = node[key]
    if (Array.isArray(child)) return child.some((item) => containsHoistedDeclaration(item, false))
    return containsHoistedDeclaration(child, false)
  })
}

function isIdentifierName(value) {
  return /^[A-Za-z_$][0-9A-Za-z_$]*$/.test(value)
}

function isSafeUnusedInitializer(node) {
  if (!node) return true
  if (
    t.isStringLiteral(node) ||
    t.isNumericLiteral(node) ||
    t.isBooleanLiteral(node) ||
    t.isNullLiteral(node) ||
    t.isBigIntLiteral(node) ||
    t.isRegExpLiteral(node) ||
    t.isFunctionExpression(node) ||
    t.isArrowFunctionExpression(node)
  ) {
    return true
  }
  if (t.isUnaryExpression(node)) {
    return ['!', 'void', 'typeof'].includes(node.operator) && isSafeUnusedInitializer(node.argument)
  }
  if (t.isTemplateLiteral(node)) {
    return node.expressions.length === 0
  }
  if (t.isArrayExpression(node)) {
    return node.elements.every((element) => element === null || (!t.isSpreadElement(element) && isSafeUnusedInitializer(element)))
  }
  if (t.isObjectExpression(node)) {
    return node.properties.every((property) =>
      t.isObjectProperty(property) && !property.computed && isSafeUnusedInitializer(property.value)
    )
  }
  return false
}

const visitors = {
  deleteExtra: {
    StringLiteral(path) {
      delete path.node.extra
    },
    NumericLiteral(path) {
      delete path.node.extra
    }
  },

  foldBinary: {
    BinaryExpression: {
      exit(path) {
        const evaluation = path.evaluate()
        if (!evaluation.confident) return
        if (typeof evaluation.value === 'function') return
        path.replaceWith(t.valueToNode(evaluation.value))
      }
    }
  },

  foldBooleanObfuscation: {
    UnaryExpression(path) {
      if (path.node.operator !== '!') return
      const arg = path.node.argument
      if (t.isArrayExpression(arg) && arg.elements.length === 0) {
        path.replaceWith(t.booleanLiteral(false))
        return
      }
      if (!t.isUnaryExpression(arg, { operator: '!' })) return
      const nested = arg.argument
      if (t.isArrayExpression(nested) && nested.elements.length === 0) {
        path.replaceWith(t.booleanLiteral(true))
      }
    }
  },

  mergeStrings: {
    BinaryExpression: {
      exit(path) {
        if (path.node.operator !== '+') return
        const left = path.node.left
        const right = path.node.right
        if (!t.isStringLiteral(left) || !t.isStringLiteral(right)) return
        path.replaceWith(t.stringLiteral(left.value + right.value))
      }
    }
  },

  normalizeMember: {
    MemberExpression(path) {
      if (!path.node.computed) return
      if (!t.isStringLiteral(path.node.property)) return
      const value = path.node.property.value
      if (!isIdentifierName(value)) return
      path.node.property = t.identifier(value)
      path.node.computed = false
    }
  },

  removeEmpty: {
    EmptyStatement(path) {
      path.remove()
    }
  },

  splitSequenceStatements: {
    ExpressionStatement(path) {
      if (!t.isSequenceExpression(path.node.expression)) return
      const statements = path.node.expression.expressions.map((expr) => t.expressionStatement(expr))
      path.replaceWithMultiple(statements)
    }
  },

  removeUnusedVariables: {
    VariableDeclarator(path) {
      if (!t.isIdentifier(path.node.id)) return
      const binding = path.scope.getBinding(path.node.id.name)
      if (!binding || binding.referenced || !binding.constant) return
      if (binding.scope.path.isProgram()) return
      const declaration = path.parentPath
      const parent = declaration.parentPath
      if (parent.isProgram()) return
      if (!isSafeUnusedInitializer(path.node.init)) return
      if (t.isForInStatement(parent?.node) || t.isForOfStatement(parent?.node)) return
      if (declaration.node.declarations.length === 1) {
        declaration.remove()
        declaration.scope.crawl()
        return
      }
      path.remove()
      path.scope.crawl()
    }
  },

  constantIf: {
    IfStatement(path) {
      const evaluation = path.get('test').evaluate()
      if (!evaluation.confident) return
      if (evaluation.value) {
        if (containsHoistedDeclaration(path.node.alternate)) return
        if (t.isBlockStatement(path.node.consequent)) {
          path.replaceWith(t.cloneNode(path.node.consequent, true))
        } else {
          path.replaceWith(path.node.consequent)
        }
        return
      }
      if (containsHoistedDeclaration(path.node.consequent)) return
      if (!path.node.alternate) {
        path.remove()
        return
      }
      if (t.isBlockStatement(path.node.alternate)) {
        path.replaceWith(t.cloneNode(path.node.alternate, true))
      } else {
        path.replaceWith(path.node.alternate)
      }
    }
  },

  awscVoid: {
    UnaryExpression(path) {
      if (path.node.operator !== 'void') return
      if (!path.parentPath.isExpressionStatement()) return
      if (t.isSequenceExpression(path.node.argument)) return
      const evaluation = path.get('argument').evaluate()
      if (evaluation.confident && typeof evaluation.value === 'string') return
      path.replaceWith(path.node.argument)
    }
  },

  awscLogicalToIf: {
    LogicalExpression(path) {
      if (path.node.operator !== '&&') return
      if (!path.parentPath.isExpressionStatement()) return
      path.parentPath.replaceWith(
        t.ifStatement(path.node.left, t.blockStatement([t.expressionStatement(path.node.right)]))
      )
    }
  },

  awscConditionalToIf: {
    ConditionalExpression(path) {
      if (!path.parentPath.isExpressionStatement()) return
      path.parentPath.replaceWith(
        t.ifStatement(
          path.node.test,
          t.blockStatement([t.expressionStatement(path.node.consequent)]),
          t.blockStatement([t.expressionStatement(path.node.alternate)])
        )
      )
    }
  },

  awscNormalizeBlocks: {
    IfStatement(path) {
      if (!t.isBlockStatement(path.node.consequent)) {
        path.node.consequent = t.blockStatement([path.node.consequent])
      }
      if (path.node.alternate && !t.isBlockStatement(path.node.alternate) && !t.isIfStatement(path.node.alternate)) {
        path.node.alternate = t.blockStatement([path.node.alternate])
      }
    },
    BlockStatement(path) {
      const nextBody = []
      let changed = false
      for (const statement of path.node.body) {
        if (t.isBlockStatement(statement)) {
          changed = true
          nextBody.push(...statement.body)
        } else {
          nextBody.push(statement)
        }
      }
      if (changed) {
        path.node.body = nextBody
      }
    }
  },

  whileSwitchUnwrap: {
    WhileStatement: {
      exit(path) {
        const body = path.node.body
        if (!t.isBlockStatement(body) || body.body.length === 0) return
        const first = body.body[0]
        if (!t.isSwitchStatement(first)) return

        const test = path.node.test
        const isForever =
          t.isBooleanLiteral(test, { value: true }) ||
          (t.isUnaryExpression(test, { operator: '!' }) && t.isNumericLiteral(test.argument, { value: 0 }))
        if (!isForever) return

        const discriminant = first.discriminant
        if (!t.isMemberExpression(discriminant)) return
        if (!t.isIdentifier(discriminant.object)) return

        let indexName = null
        if (t.isUpdateExpression(discriminant.property) && t.isIdentifier(discriminant.property.argument)) {
          indexName = discriminant.property.argument.name
        } else if (t.isIdentifier(discriminant.property)) {
          indexName = discriminant.property.name
        }
        if (!indexName) return

        const orderBinding = path.scope.getBinding(discriminant.object.name)
        if (!orderBinding) return
        const init = orderBinding.path.node.init
        if (!t.isCallExpression(init) || !t.isMemberExpression(init.callee)) return
        if (!t.isStringLiteral(init.callee.object)) return
        if (!t.isIdentifier(init.callee.property, { name: 'split' })) return
        if (init.arguments.length !== 1 || !t.isStringLiteral(init.arguments[0], { value: '|' })) return

        const order = init.callee.object.value.split('|')
        const caseMap = new Map()
        for (const switchCase of first.cases) {
          if (!switchCase.test) continue
          if (!t.isStringLiteral(switchCase.test) && !t.isNumericLiteral(switchCase.test)) continue
          caseMap.set(String(switchCase.test.value), switchCase)
        }

        const flattened = []
        for (const key of order) {
          const switchCase = caseMap.get(String(key))
          if (!switchCase) continue
          for (const statement of switchCase.consequent) {
            if (t.isContinueStatement(statement) || t.isBreakStatement(statement)) {
              break
            }
            flattened.push(t.cloneNode(statement, true))
            if (t.isReturnStatement(statement)) {
              break
            }
          }
        }

        if (flattened.length > 0) {
          path.replaceWithMultiple(flattened)
        }
      }
    }
  }
}

function runCommon(ast) {
  applyVisitors(ast, [
    visitors.deleteExtra,
    visitors.foldBinary,
    visitors.foldBooleanObfuscation,
    visitors.mergeStrings,
    visitors.normalizeMember,
    visitors.splitSequenceStatements,
    visitors.constantIf,
    visitors.removeEmpty,
    visitors.removeUnusedVariables
  ])
  return ast
}

function runAwsc(ast, options = {}) {
  const selectedVisitors = [
    visitors.awscVoid,
    visitors.awscConditionalToIf,
    visitors.awscLogicalToIf
  ]
  if (options.aggressive) selectedVisitors.push(visitors.awscNormalizeBlocks)
  applyVisitors(ast, selectedVisitors)
  return runCommon(reparse(ast))
}

function runObfuscator(ast, options = {}) {
  const selectedVisitors = options.aggressive
    ? [visitors.whileSwitchUnwrap, visitors.normalizeMember]
    : [visitors.normalizeMember]
  applyVisitors(ast, selectedVisitors)
  return runCommon(reparse(ast))
}

function runSojson(ast) {
  // Template entry point only.
  // For a real target, add a dedicated decrypt bootstrap pass here.
  return runCommon(ast)
}

function familyScore(code) {
  const ast = parseCode(code)
  const features = {
    hexIdentifiers: 0,
    debuggerStatements: 0,
    setIntervalCalls: 0,
    splitPipeCalls: 0,
    whileSwitchLoops: 0,
    dispatcherTables: 0,
    voidExpressions: 0,
    conditionalExpressions: 0,
    logicalAndExpressions: 0,
    jjencode: 0
  }

  traverse(ast, {
    Identifier(path) {
      if (/^_0x[0-9a-f]+$/i.test(path.node.name)) features.hexIdentifiers++
      if (path.node.name === '$___' || path.node.name.includes('$$$')) features.jjencode = 10
    },
    DebuggerStatement() {
      features.debuggerStatements++
    },
    CallExpression(path) {
      const callee = path.node.callee
      const isSetInterval =
        t.isIdentifier(callee, { name: 'setInterval' }) ||
        (t.isMemberExpression(callee) && t.isIdentifier(callee.property, { name: 'setInterval' }))
      if (isSetInterval) features.setIntervalCalls++
      if (
        t.isMemberExpression(callee) &&
        t.isIdentifier(callee.property, { name: 'split' }) &&
        path.node.arguments.length === 1 &&
        t.isStringLiteral(path.node.arguments[0], { value: '|' })
      ) {
        features.splitPipeCalls++
      }
    },
    WhileStatement(path) {
      const test = path.node.test
      const isForever =
        t.isBooleanLiteral(test, { value: true }) ||
        (t.isUnaryExpression(test, { operator: '!' }) && t.isNumericLiteral(test.argument, { value: 0 }))
      if (isForever && t.isBlockStatement(path.node.body) && path.node.body.body.some(t.isSwitchStatement)) {
        features.whileSwitchLoops++
      }
    },
    VariableDeclarator(path) {
      if (!t.isObjectExpression(path.node.init)) return
      if (path.node.init.properties.some((property) =>
        t.isObjectProperty(property) &&
        (t.isFunctionExpression(property.value) || t.isArrowFunctionExpression(property.value))
      )) {
        features.dispatcherTables++
      }
    },
    UnaryExpression(path) {
      if (path.node.operator === 'void') features.voidExpressions++
    },
    ConditionalExpression() {
      features.conditionalExpressions++
    },
    LogicalExpression(path) {
      if (path.node.operator === '&&') features.logicalAndExpressions++
    }
  })

  const hasHexFamily = features.hexIdentifiers >= 2
  return {
    hexIdentifiers: features.hexIdentifiers,
    sojson: Number(hasHexFamily) + Number(features.debuggerStatements > 0),
    sojsonv7: Number(hasHexFamily) + Number(features.setIntervalCalls > 0),
    obfuscator:
      Number(hasHexFamily) +
      Number(features.splitPipeCalls > 0) +
      Number(features.whileSwitchLoops > 0) +
      Number(features.dispatcherTables > 0),
    awsc:
      Number(features.voidExpressions > 0) +
      Number(features.conditionalExpressions > 0) +
      Number(features.logicalAndExpressions > 0),
    jjencode: features.jjencode
  }
}

function isOnlyFamilyMatch(score, family) {
  const matches = {
    sojsonv7: score.sojsonv7 >= 2,
    sojson: score.sojson >= 2,
    obfuscator: score.obfuscator >= 2,
    awsc: score.awsc >= 2
  }
  return matches[family] && Object.values(matches).filter(Boolean).length === 1
}

const plugins = [
  {
    name: 'sojsonv7',
    detect(code) {
      const score = familyScore(code)
      return isOnlyFamilyMatch(score, 'sojsonv7')
    },
    transform(code) {
      return generateCode(runSojson(parseCode(code)))
    }
  },
  {
    name: 'sojson',
    detect(code) {
      const score = familyScore(code)
      return isOnlyFamilyMatch(score, 'sojson')
    },
    transform(code) {
      return generateCode(runSojson(parseCode(code)))
    }
  },
  {
    name: 'obfuscator',
    detect(code) {
      const score = familyScore(code)
      return isOnlyFamilyMatch(score, 'obfuscator')
    },
    transform(code, options) {
      return generateCode(runObfuscator(parseCode(code), options))
    }
  },
  {
    name: 'awsc',
    detect(code) {
      const score = familyScore(code)
      return isOnlyFamilyMatch(score, 'awsc')
    },
    transform(code, options) {
      return generateCode(runAwsc(parseCode(code), options))
    }
  },
  {
    name: 'common',
    detect() {
      return true
    },
    transform(code) {
      return generateCode(runCommon(parseCode(code)))
    }
  }
]

function getArg(flag, fallback) {
  const index = process.argv.indexOf(flag)
  if (index === -1 || index + 1 >= process.argv.length) return fallback
  return process.argv[index + 1]
}

function main() {
  const inputFile = getArg('-i', 'input.js')
  const outputFile = getArg('-o', 'output.js')
  const code = fs.readFileSync(inputFile, 'utf8')
  parseCode(code)
  const aggressive = process.argv.includes('--aggressive')

  let result = code
  let pluginUsed = 'common'

  for (const plugin of plugins) {
    if (!plugin.detect(code)) continue
    try {
      const candidate = plugin.transform(code, { aggressive })
      parseCode(candidate)
      if (candidate && candidate !== code) {
        result = candidate
        pluginUsed = plugin.name
        break
      }
    } catch (error) {
      throw new Error(`[${plugin.name}] transform failed: ${error.message}`)
    }
  }

  const banner = [
    '// generated by decode_action_scaffold',
    `// plugin: ${pluginUsed}`,
    `// input: ${path.basename(inputFile)}`,
    ''
  ].join('\n')

  fs.writeFileSync(outputFile, banner + result, 'utf8')
  console.log(`plugin=${pluginUsed}`)
  console.log(`output=${outputFile}`)
}

main()
