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
     .delete-btn { background: #cf6679; color: white; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; border: none; cursor: pointer; }
     .delete-btn:hover { background: #d34458; }
     .edit-btn { background: #ffd000; color: black; padding: 5px 10px; border-radius: 4px; text-decoration: none; font-size: 12px; border: none; cursor: pointer; margin-right: 5px; }
     .edit-btn:hover { background: #ffc107; }
     .device-actions { display: flex; gap: 5px; }
     #device-list { list-style: none; padding: 0; }
    </style>
</head>
<body>
    <div class="container">
      <h1>LightchangerT Configuration</h1>
      <form action="/save" method="POST">
        <input type="hidden" name="edit_mode" id="edit_mode" value="">
        <input type="hidden" name="edit_idx" id="edit_idx" value="">

        <label>IP Address</label>
        <input type="text" name="ip" id="ip" placeholder="192.168.1.100" required>

        <label>Brand</label>
        <select name="brand" id="brand">
          <option value="sony">Sony (Blue)</option>
          <option value="microsoft">Microsoft (Green)</option>
          <option value="nintendo">Nintendo (Red)</option>
          <option value="steam">Steam (Light Blue)</option>
          <option value="nvidia">Nvidia (Light Green)</option>
        </select>

        <button type="submit" id="submit-btn">Add Device</button>
      </form>

      <div class="device-list">
        <h3 style="color: #bb86fc; margin-top: 20px;">Configured Devices (<span id="device-count">0</span>)</h3>
        <ul id="device-list"></ul>
        <button onclick="document.getElementById('clear-form').style.display='block'" style="margin-top: 10px; background: #cf6679; color: white;">Clear All Devices</button>
        <form id="clear-form" action="/clear" method="POST" style="display: none;">
          <button type="submit">Confirm All Clear</button>
        </form>
      </div>

      <div class="status" id="status-msg"></div>
    </div>

    <script>
     async function loadDevices() {
       try {
         const res = await fetch('/api/devices');
         const devices = await res.json();
         const list = document.getElementById('device-list');
         const count = document.getElementById('device-count');
         list.innerHTML = '';
         count.textContent = devices.length;

         devices.forEach((dev, idx) => {
           const li = document.createElement('li');
           li.className = 'device';
           li.innerHTML = '<span>' + dev.ip + ' - ' + dev.brand + '</span>' +
              '<div class="device-actions">' +
                '<button class="edit-btn" onclick="editDevice(' + idx + ')">Edit</button>' +
                '<button class="delete-btn" onclick="deleteDevice(' + idx + ')">Delete</button>' +
              '</div>';
           list.appendChild(li);
         });
         } catch(e) {
         document.getElementById('status-msg').textContent = 'Error loading devices: ' + e;
         }
        }

      function editDevice(idx) {
        fetch('/api/device?idx=' + idx).then(r => r.json()).then(dev => {
          document.getElementById('ip').value = dev.ip;
          document.getElementById('brand').value = dev.brand;
          document.getElementById('edit_mode').value = '1';
          document.getElementById('edit_idx').value = idx;
          document.getElementById('submit-btn').textContent = 'Update Device';
          loadDevices();
          });
         }

      function deleteDevice(idx) {
        if (!confirm('Delete this device?')) return;
        fetch('/api/device?idx=' + idx, { method: 'DELETE' }).then(() => {
          document.getElementById('status-msg').textContent = 'Device deleted!';
          loadDevices();
          });
         }

      document.getElementById('clear-form').style.display = 'none';
      loadDevices();
     </script>
</body>
</html>
)rawl";

#endif
