#ifndef WEB_UI_H
#define WEB_UI_H

#include <Arduino.h>

const char INDEX_HTML[] PROGMEM = R"rawl(
<!DOCTYPE html>
<html>
<head>
  <title>LightchangerT Config</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body { background-color: #121212; color: #e0e0e0; font-family: sans-serif; margin: 0; padding: 20px; }
    h1 { color: #ffffff; text-align: center; }
    .container { max-width: 600px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.5); }
    label { display: block; margin-top: 15px; font-weight: bold; color: #bb86fc; }
    input, select { width: 100%; padding: 10px; margin-top: 5px; background: #2d2d2d; border: 1px solid #444; color: white; border-radius: 4px; box-sizing: border-box; }
    button { width: 100%; padding: 12px; margin-top: 20px; background-color: #bb86fc; color: black; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; font-weight: bold; }
    button:hover { background-color: #9965f4; }
    .status { margin-top: 20px; padding: 10px; background: #333; border-radius: 4px; text-align: center; }
    .device-list { margin-top: 20px; border-top: 1px solid #444; }
    .device { background: #2d2d2d; padding: 10px; margin-top: 10px; border-radius: 4px; display: flex; justify-content: space-between; align-items: center; }
    .delete-btn { background: #cf6679; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; }
  </style>
</head>
<body>
  <div class="container">
    <h1>LightchangerT Configuration</h1>
    <form action="/save" method="POST">
      <label>IP Address</label>
      <input type="text" name="ip" placeholder="192.168.1.100" required>

      <label>Brand</label>
      <select name="brand">
        <option value="sony">Sony (Blue)</option>
        <option value="microsoft">Microsoft (Green)</option>
        <option value="nintendo">Nintendo (Red)</option>
        <option value="steam">Steam (Light Blue)</option>
        <option value="nvidia">Nvidia (Light Green)</option>
      </select>

      <button type="submit">Add Device</button>
    </form>

    <div class="status">Devices are checked every scan interval.</div>
  </div>
</body>
</html>
)rawl";

#endif