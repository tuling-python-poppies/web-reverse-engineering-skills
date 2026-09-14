/**
 * Synthetic Akamai-shape sensor for the offline NV8 proof.
 *
 * This is NOT the real adidas HK sensor JavaScript (sensitive material is
 * intentionally excluded from the case). It only reproduces the documented
 * observable contract:
 *   - runs inside the NV8 page
 *   - asynchronously POSTs JSON {"body": "<encoded>"} (> 4000 bytes)
 *   - to the sensor endpoint derived from the challenge script URL
 *
 * The runner injects `globalThis.__SENSOR_ENDPOINT` before evaluating this
 * script; the endpoint always matches `fixtures/challenge.html`.
 */
(function () {
  var endpoint = globalThis.__SENSOR_ENDPOINT;
  if (typeof endpoint !== 'string' || endpoint.indexOf('synthMount') === -1) {
    throw new Error('synthetic sensor: __SENSOR_ENDPOINT missing');
  }

  // Deterministic >= 4000-byte encoded payload; shape mirrors the documented
  // sensor request body (single JSON key "body").
  var encoded = new Array(4200).join('x');
  var body = JSON.stringify({ body: encoded });

  setTimeout(function () {
    fetch(endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: body,
    }).catch(function () {
      /* offline boundary may reject; the runner captures the request anyway */
    });
  }, 50);
})();
