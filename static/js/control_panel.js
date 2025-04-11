function getValueForId(id) {
    return document.getElementById(id).value;
}

async function getControlPanelData() {
    const request = new Request('/control-panel-data');

    fetch(request)
    .then(response => {
        if(!response.ok) {
            throw new Error('Network response error');
        }
        return response.json();
    })
    .then(data => {
        if(data) {
            // Populate hotspot/SSID data
            for(const [key, value] of Object.entries(data.ssid_info)) {
                document.getElementById(key).innerHTML = value;
            }

            // Populate STA data
            for(const [key, value] of Object.entries(data.sta)) {
                document.getElementById(key).innerHTML = value;
            }

            // Determine what displays on page
            document.getElementById("disconnect-form").style.display = data.connected ? '' : 'none';
            document.getElementById("sta-disconnect-form").style.display = data.connected ? '' : 'none';

            if(data.connected) {
                if(data.saved_connection_exists && data.sta.saved_ssid != null) {
                
                    if(data.ssid_info.saved_ssid == data.sta.sta_ssid) {
                        document.getElementById("delete-connection-form").style.display = '';
                    }
                    else {
                        let owForm = document.getElementById("overwrite-connection-form");
                        owForm.style.display = '';
                        // add in ssid and password
                        document.getElementById("delete-connection-form").style.display = '';
                    }
            }
            else {
                document.getElementById("save-connection-form").style.display = '';
            }
            }
            else {
                if(data.saved_connection_exists) {
                    document.getElementById("delete-connection-form").style.display = '';
                }
            }
        }
    })
}

async function populateNetworks() {
    
    message = document.getElementById("loading-message");
    message.style.display = '';

    const request = new Request('/scan_networks');

    fetch(request)
    .then(response => {
        if(!response.ok) {
        throw new Error('Network response error');
        }
        return response.json();
    })
    .then(data => {

        if (data) {
        // Data found, remove everything in list.
        selectList = document.getElementById("network-select");
        selectList.innerHTML = "";
        
        data.forEach(function(ssid) {
            // Create new option for the SSID and add to list.
            selectList.appendChild(createOption(ssid, ssid));
        });
        }
    })
    .catch(error => {
        console.error("Could not load JSON data");
    })
    .finally(() => {
        message.style.display = 'none';
    });
}


function addTrigger(t) {

    var num = document.getElementsByClassName("trigger-count").length;

    triggerRow = document.getElementById(t);

    let name = document.createElement("input");
    name.id = `trigger-${num}-name`;
    name.type = "text";

    triggerRow.appendChild(name);

    let triggerInput = document.createElement("select");
    triggerInput.id = `trigger-${num}-input`;
    Array(6).keys().forEach(i => {
        triggerInput.append(createOption(i + 1, `Input ${i + 1}`));
    });

    triggerRow.appendChild(triggerInput);

    let triggerMode = document.createElement("select")
    triggerMode.id = `trigger-${num}-mode`;
    triggerMode.append(createOption("Remote", "Remote"));
    triggerMode.append(createOption("SVS", "SVS"));
    triggerRow.appendChild(triggerMode)

    let triggerProfile = document.createElement("select");
    triggerProfile.id = `trigger-${num}-profile`;
    Array(12).keys().forEach(i => {
        triggerProfile.appendChild(createOption(i + 1, `Profile ${i + 1}`));
    });

    triggerRow.appendChild(triggerProfile);
}

function createOption(value, text) {
    let x = document.createElement("option");
    x.value = value;
    x.text = text

    return x;
}

function toggle() {
    let x = getValueForId("tcp-server-enabled");
    let y = getValueForId("tcp-server-port");

    y.disabled = !(x === "true");
}

function toggleSerialTelnet() {
    var x = getValueForId("extron-connection");
    
    var s = getValueForId("extron-serial");
    var t = getValueForId("extron-telnet");

    if(x.value === "telnet") {
        s.style.display = 'none';
        t.style.display = '';
    }
    else {
        s.style.display = '';
        t.style.display = 'none';
    }
}

function buildJson() {
    tink = {
        txPin: +getValueForId("tink-tx-pin"),
        rxPin: +getValueForId("tink-rx-pin"),
        uartId: +getValueForId("tink-uart")
    }

    tcpServer = {
        enabled: +getValueForId("tcp-server-enabled") === "true",
        port: +getValueForId("tcp-server-port")
    }

    switcher = {
        enabled: +getValueForId("extron-")
    }

    j = {
        tink: tink,
        tcpServer: tcpServer
    };

    return j;
}