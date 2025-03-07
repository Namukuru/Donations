//Message timing out: after 2 seconds
setTimeout(function () {
    var alertMessage = document.getElementById("alertMessage");
    if (alertMessage) {
      alertMessage.remove();
    }
  }, 2000);