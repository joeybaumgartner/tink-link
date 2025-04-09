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
          // Create new option for the SSID
          let option = document.createElement("option");
          option.value = ssid;
          option.text = ssid;

          // Add option to SSID list.
          selectList.appendChild(option);
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