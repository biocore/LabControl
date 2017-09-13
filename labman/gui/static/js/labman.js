// This variable is needed to control the bootstrap alert correctly
var timeoutHandleForBoostrapAlert = null;

/**
 * Adds a Bootstrap alert message to the body of the current page.
 *
 * @param message: Message to display
 * @param severity: OPTIONAL. One of 'danger' (default), 'info', 'warning' or 'success'.
 * @param timeout: OPTIONAL. When given, seconds before alert fades out
 *
 **/
function bootstrapAlert(message, severity, timeout){
  $('.modal').modal('hide');
  // make timeout an optional parameter
  timeout = timeout || -1;
  // make severity an optinal parameter
  severity = typeof severity !== 'undefined' ? severity : 'danger';
  // Remove any previous alert message
  $("#alert-message").remove();
  // Crate the div that contains the message and append the alert message
  var alertDiv = $('<div>', { 'class': 'alert fade in alert-'+severity, 'role': 'alert', 'id': 'alert-message'})
    .append('<a href="#" class="close" data-dismiss="alert">&times;</a>')
    .append('<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span>')
    .append(message);
  // Add the alert div just under the navbar
  $('#template-content').prepend(alertDiv);
  // Set a timeout for the alert div if needed
  if(timeout > 0) {
   if (timeoutHandleForBoostrapAlert != null) {
     // This is needed in case that a new alert is generated while
     // an alert is already shown
     window.clearTimeout(timeoutHandleForBoostrapAlert);
   }
   timeoutHandleForBoostrapAlert = window.setTimeout(function() {
     $('#alert-message').remove();
     timeoutHandleForBoostrapAlert = null;
   }, timeout*1000); // * 1000 to transform from seconds to miliseconds
  }
}
