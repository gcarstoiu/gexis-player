// SPDX-License-Identifier: GPL-3.0-or-later
// ADR-0152: the description this player serves, tried against this player.
window.ui = SwaggerUIBundle({
  url: "openapi.json",
  dom_id: "#api",
  deepLinking: true,
  tryItOutEnabled: true,
  displayRequestDuration: true,
  docExpansion: "none",
  defaultModelsExpandDepth: 0,
});
