// This variable is needed to control the bootstrap alert correctly
var timeoutHandleForBoostrapAlert = null;

// Disable all inputs from a page
function disableAll() {
  $('input').prop('disabled', true);
  $('select').prop('disabled', true);
  $('button').prop('disabled', true);
}

/**
 *
 * Auxiliary function to set up a Plate Name input
 *
 * @param $targetDiv Element The target DIV to append the input
 * @param plateId integer The plate id to uniquely identify the elements
 * @param checksCallback function Callback to execute when the input changes
 * @param label string Input label
 * @param defaultValue string The input default value
 *
 **/
function createPlateNameInputDOM($targetDiv, plateId, checksCallback, label, defaultValue) {
  var $rowDiv = $('<div>').addClass('form-group').appendTo($targetDiv);
  $('<label>').attr('for', 'plate-name-' + plateId).addClass('col-sm-2 control-label').append(label).appendTo($rowDiv);
  var $colDiv = $('<div>').attr('id', 'div-plate-name-' + plateId).addClass('col-sm-10 has-feedback').appendTo($rowDiv);
  $('<span>').addClass('glyphicon glyphicon-remove form-control-feedback').appendTo($colDiv);
  var $inElem = $('<input>').attr('type', 'text').addClass('form-control').attr('id', 'plate-name-' + plateId).val(defaultValue).appendTo($colDiv);
  $inElem.keyup(function(e) {
    onKeyUpPlateName(e, 'plate-name-' + plateId, checksCallback);
  });
  $inElem.ready(function() {
    var e = $.Event('keyup');
    $('#plate-name-' + plateId).trigger(e);
  });
  return $rowDiv;
}

function createNumberInputDOM($targetDiv, plateId, checksCallback, label, defaultValue, idPrefix, step, minVal) {
  var $rowDiv = $('<div>').addClass('form-group').appendTo($targetDiv);
  $('<label>').attr('for', idPrefix + plateId).addClass('col-sm-2 control-label').append(label).appendTo($rowDiv);
  var $colDiv = $('<div>').addClass('col-sm-10').appendTo($rowDiv);
  var $inElem = $('<input>').attr('type', 'number').addClass('form-control')
                            .attr('id', idPrefix + plateId).val(defaultValue)
                            .appendTo($colDiv).on('change', checksCallback)
                            .attr('step', step).attr('min', minVal);
  return $rowDiv;
}

function createSelectDOM($targetDiv, plateId, checksCallback, label, options, idPrefix, placeholder, idKey) {
  if (idKey === undefined) {
    idKey = 'equipment_id';
  }
  var $rowDiv = $('<div>').addClass('form-group').appendTo($targetDiv);
  $('<label>').attr('for', idPrefix + plateId).addClass('col-sm-2 control-label').append(label).appendTo($rowDiv);
  var $colDiv = $('<div>').addClass('col-sm-10').appendTo($rowDiv);
  var $selElem = $('<select>').addClass('form-control').attr('plate-id', plateId).attr('id', idPrefix + plateId).appendTo($colDiv).on('change', checksCallback);
  $('<option>').prop('selected', true).prop('disabled', true).append(placeholder).appendTo($selElem);
  $.each(options, function(idx, elem){
    $('<option>').attr('value', elem[idKey]).append(elem.external_id).appendTo($selElem)
  });
}

function createReagentDOM($targetDiv, plateId, checksCallback, label, idPrefix, vueTarget, reagentType) {
  var $rowDiv = $('<div>').addClass('form-group').appendTo($targetDiv);
  $('<label>').attr('for', idPrefix + plateId).addClass('col-sm-2 control-label').append(label).appendTo($rowDiv);
  var $colDiv = $('<div>').addClass('col-sm-10').appendTo($rowDiv);
  var $inElem = $('<input>').attr('type', 'text').addClass('form-control').attr('id', idPrefix + plateId).appendTo($colDiv);
  // Add the Vue element to the extraction kit once it has been loaded into the DOM.
  // This is needed otherwise Vue will not find the input element
  $inElem.ready( function() {
    var vueContainer = $('<div>').attr('id', 'vue-elem-' + idPrefix + plateId).appendTo(vueTarget);
    var vueComponentCtr = Vue.extend(ReagentModalComponent);
    var vueElem = new vueComponentCtr({propsData: {'idPrefix': idPrefix + plateId, 'reagentType': reagentType,
                                                   'inputTarget': idPrefix + plateId, 'checksCallback': checksCallback}});
    vueElem.$mount('#vue-elem-' + idPrefix + plateId);
  });
}

/**
 *
 * Auxiliary function to check the availability of a plate name as the
 * user types it
 *
 * @param e event The event object from the key up function
 * @param input str The name of the input element
 * @param checksCallback function Callback function to change the rest of the interface
 * @param successCallback function Callback function to execute when the user hits enter and the name doesn't exist
 *
 * Notes: for this function to work properly, the input should be contained
 * in a structure like the one below. The div can contain an optional label.
 *
 * <div class='form-group has-error has-feedback'>
 *  **** <label for='newNameInput'>New name:</label>   <---- This label is optional
 *  <input type='text' class='form-control' id='<>INPUT ID'>
 *  <span class='glyphicon glyphicon-remove form-control-feedback'></span>
 * </div>
 *
 **/
function onKeyUpPlateName(e, input, checksCallback, successCallback) {
  // Check if the new value is the empty string
  var value = $('#' + input).val().trim()
  var $div = $('#' + input).closest('div');
  if (value !== '') {
    $.get('/platename?new-name=' + value, function (data) {
      // If we get here it means that the name already exists
      $div.removeClass('has-success').addClass('has-error').find('span').removeClass('glyphicon-ok').addClass('glyphicon-remove');
      // $('#updateNameBtn').prop('disabled', true);
      checksCallback();
    })
      .fail(function (jqXHR, textStatus, errorThrown) {
        // We need to check the status of the response
        if(jqXHR.status === 404) {
          // The plate name doesn't exist - it is ok to change to this name
          $div.removeClass('has-error').addClass('has-success').find('span').removeClass('glyphicon-remove').addClass('glyphicon-ok');
          // $('#updateNameBtn').prop('disabled', false);
          checksCallback();
          if(e.which == 13 && successCallback !== undefined) {
            // This means that the user pressed the enter key
            // so we will just call the success callback
            successCallback();
          }
        } else {
          bootstrapAlert(jqXHR.responseText, 'danger');
          checksCallback();
        }
      });
  } else {
    $div.removeClass('has-success').addClass('has-error').find('span').removeClass('glyphicon-ok').addClass('glyphicon-remove');
    // $('#updateNameBtn').prop('disabled', true);
    checksCallback();
  }
}

/**
 * Adds a Bootstrap alert message to the body of the current page.
 *
 * @param {string} message Message to display
 * @param {string} severity OPTIONAL. One of 'danger' (default), 'info', 'warning' or 'success'.
 * @param {integer} timeout OPTIONAL. When given, seconds before alert fades out
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

/**
 *
 * Get's the next row id
 * Adapted from: https://stackoverflow.com/a/34483399
 *
 * @param {char} row The current row id
 *
 * @return {string}
 *
 **/
function getNextRowId(row) {
  var u = row.toUpperCase();
  if (sameStrChar(u, 'Z')){
    var txt = '';
    var i = u.length;
    while (i--) {
      txt += 'A';
    }
    return (txt + 'A');
  } else {
    var p = "";
    var q = "";
    if (u.length > 1) {
      p = u.substring(0, u.length - 1);
      q = String.fromCharCode(p.slice(-1).charCodeAt(0));
    }
    var l = u.slice(-1).charCodeAt(0);
    var z = nextLetter(l);
    if (z === 'A') {
      return p.slice(0, -1) + nextLetter(q.slice(-1).charCodeAt(0)) + z;
    } else {
      return p + z;
    }
  }
};

/**
 *
 * Aux function for getNextRowId
 * Returns the letter after the given one
 *
 * @param {char} l The current letter
 *
 * @return {char} The next letter
 *
 **/
function nextLetter(l) {
  if (l < 90) {
    return String.fromCharCode(l + 1);
  } else {
    return 'A';
  }
};

/**
 *
 * Aux function for getNextRowId
 * Returns if str and char are the same
 *
 * @param {str} str The string to compare
 * @param {char} char The char to compare
 *
 * @return {char} The next letter
 *
 **/
function sameStrChar(str, char) {
  var i = str.length;
  while (i--) {
    if (str[i] !== char) {
      return false;
    }
  }
  return true;
}
