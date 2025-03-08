var ws;
// Timers for handling hold behavior.
var holdTimeouts = {};
var holdIntervals = {};
// Repeat interval (in ms); here, 50ms = 20 times per second.
var repeatInterval = 50;

function initWebSocket() {
  ws = new WebSocket("ws://" + location.host + "/ws");
  ws.onopen = function() {
    console.log("WebSocket connected");
  };
  ws.onmessage = function(event) {
    console.log("Received from server: " + event.data);
  };
  ws.onerror = function(error) {
    console.error("WebSocket error:", error);
  };
  ws.onclose = function() {
    console.log("WebSocket closed, reconnecting in 2s...");
    setTimeout(initWebSocket, 2000);
  };
}

// Send a base command to the server.
function sendZoneCommand(command) {
  console.log("Sending command: " + command);
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(command);
  } else {
    console.log("WebSocket not connected");
  }
}

// On press: send the base command immediately, then start repeating after 1 second.
function handlePress(command) {
  sendZoneCommand(command);
  holdTimeouts[command] = setTimeout(function() {
    holdIntervals[command] = setInterval(function() {
      sendZoneCommand(command);
    }, repeatInterval);
  }, 1000);
}

// On release: cancel any pending timers.
function handleRelease(command) {
  if (holdTimeouts[command]) {
    clearTimeout(holdTimeouts[command]);
    holdTimeouts[command] = null;
  }
  if (holdIntervals[command]) {
    clearInterval(holdIntervals[command]);
    holdIntervals[command] = null;
  }
}

window.onload = function() {
  initWebSocket();
  var areas = document.querySelectorAll("area");
  areas.forEach(function(area) {
    // Use the alt attribute as the base command.
    var command = area.getAttribute("alt").toLowerCase();
    
    // Use pointer events for unified handling.
    area.addEventListener("pointerdown", function(e) {
      // Prevent duplicate handling
      e.preventDefault();
      handlePress(command);
    });
    area.addEventListener("pointerup", function(e) {
      e.preventDefault();
      handleRelease(command);
    });
    area.addEventListener("pointercancel", function(e) {
      e.preventDefault();
      handleRelease(command);
    });
  });
};
