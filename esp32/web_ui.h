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
        .section { margin-top: 25px; border-top: 1px solid #444; padding-top: 15px; }
        .section-title { color: #bb86fc; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
        .note { font-size: 12px; color: #888; margin-top: 5px; }
        .warning { color: #cf6679; font-size: 13px; margin-top: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>LightchangerT Configuration</h1>

        <!-- Device Management -->
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

        <!-- Remote Command Port Settings -->
        <div class="section">
            <div class="section-title">&#9889; Remote Command Port</div>
            <p style="font-size:13px; color:#aaa; margin-bottom:10px;">
                TCP port for receiving remote color commands from other devices (e.g., Raspberry Pi).
                Send commands as text: <code>COLOR:blue</code>, <code>RGB:255,0,0</code>, <code>OFF</code>.
                Requires reboot to take effect.
            </p>
            <label>TCP Port</label>
            <input type="number" name="cmd_port" id="cmd_port" min="1001" max="65535" value="10001" required>
            <div class="note">Range: 1001&#8211;65535. Default: 10001</div>
            <div class="warning">&#9888; Reboot required after changing the command port.</div>
            <button type="button" onclick="saveCmdPort()" style="margin-top: 10px;">Save Command Port</button>
        </div>

        <div class="status" id="status-msg"></div>
    </div>

    <script>
        let currentDevices = [];

        async function loadDevices() {
            try {
                const res = await fetch('/api/devices');
                currentDevices = await res.json();
                const list = document.getElementById('device-list');
                const count = document.getElementById('device-count');
                list.innerHTML = '';
                count.textContent = currentDevices.length;

                currentDevices.forEach((dev, idx) => {
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

        async function loadConfig() {
            try {
                const res = await fetch('/api/config');
                const cfg = await res.json();
                if (cfg.command_port) {
                    document.getElementById('cmd_port').value = cfg.command_port;
                }
            } catch(e) {
                // config endpoint may not exist on older firmware - ignore
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

        function saveCmdPort() {
            const port = document.getElementById('cmd_port').value;

            if (port < 1001 || port > 65535) {
                document.getElementById('status-msg').textContent = 'Invalid port. Must be 1001-65535.';
                return;
            }

            const formData = new URLSearchParams();
            formData.append('cmd_port', port);

            fetch('/save', {
                method: 'POST',
                body: formData
            }).then(r => r.text()).then(text => {
                document.getElementById('status-msg').innerHTML = text;
            }).catch(err => {
                document.getElementById('status-msg').textContent = 'Error saving: ' + err;
            });
        }

        document.getElementById('clear-form').style.display = 'none';
        loadDevices();
        loadConfig();
    </script>
</body>
</html>
)rawl";

#endif