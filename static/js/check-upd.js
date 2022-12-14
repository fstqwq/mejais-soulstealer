function sendAjaxRequest() {
  // Get the values of the concerned-id and sub-last-upd elements
  var concernedId = document.getElementById('concerned-id').textContent;
  var lastUpdate = document.getElementById('sub-last-upd').textContent;
  
  // Create an object to store the AJAX settings
  var settings = {
    url: '/recent_submission',
    data: {
      id: concernedId,
      last: lastUpdate
    },
    type: 'GET',
    success: function(response) {
      if (response.status === 'OK') {
        // Append the result to the recent-submission element
        $('#recent-submissions').html(response.result);
      } else if (response.status != 'FAILED') {
        // If the status is not OK or FAILED, try again in 2 seconds
        setTimeout(function() {
          $.ajax(settings);  // use the stored AJAX settings
        }, 2000);
      } else {
        // If the status is FAILED, show an error message
        $('#sub-updating').html('<i class="fa fa-chain-broken"></i>')
      }
    },
    error: function() {
      // This function is called if the request fails
      $('#sub-updating').html('<i class="fa fa-chain-broken"></i>')
    }
  };
  
  // Send the AJAX request using the stored settings
  $.ajax(settings);
};
if ($('#sub-updating').length > 0) {
  sendAjaxRequest();
}