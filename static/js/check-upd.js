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
      } else {
        var retries = settings.retries || 0;
        if (response.status != 'FAILED' && retries < 4) {
          settings.retries = retries + 1;
          setTimeout(function() {
            $.ajax(settings);  // use the stored AJAX settings
          }, 1500 * settings.retries); 
        } else {
          // error message
          $('#sub-updating').html('<i class="fa fa-chain-broken"></i>');
        }
      }
    },
    error: function() {
      $('#sub-updating').html('<i class="fa fa-chain-broken"></i>')
    }
  };
  
  // Send the AJAX request using the stored settings
  $.ajax(settings);
};
if ($('#sub-updating').length > 0) {
  setTimeout(sendAjaxRequest, 3500);
}