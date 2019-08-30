// This variable is needed to control the bootstrap alert correctly
var timeoutHandleForBoostrapAlert = null;

// Disable all inputs from a page
function disableAll() {
  $("input").prop("disabled", true);
  $("select").prop("disabled", true);
  $("button").prop("disabled", true);
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
function createPlateNameInputDOM(
  $targetDiv,
  plateId,
  checksCallback,
  label,
  defaultValue
) {
  var $rowDiv = $("<div>")
    .addClass("form-group")
    .appendTo($targetDiv);
  $("<label>")
    .attr("for", "plate-name-" + plateId)
    .addClass("col-sm-5 control-label")
    .append(label)
    .appendTo($rowDiv);
  var $colDiv = $("<div>")
    .attr("id", "div-plate-name-" + plateId)
    .addClass("col-sm-7 has-feedback")
    .appendTo($rowDiv);
  $("<span>")
    .addClass("glyphicon glyphicon-remove form-control-feedback")
    .appendTo($colDiv);
  var $inElem = $("<input>")
    .attr("type", "text")
    .addClass("form-control")
    .attr("id", "plate-name-" + plateId)
    .val(defaultValue)
    .appendTo($colDiv);
  $inElem.keyup(function(e) {
    onKeyUpPlateName(e, "plate-name-" + plateId, checksCallback);
  });
  $inElem.ready(function() {
    var e = $.Event("keyup");
    $("#plate-name-" + plateId).trigger(e);
  });
  return $rowDiv;
}

function createNumberInputDOM(
  $targetDiv,
  plateId,
  checksCallback,
  label,
  defaultValue,
  idPrefix,
  step,
  minVal
) {
  var $rowDiv = $("<div>")
    .addClass("form-group")
    .appendTo($targetDiv);
  $("<label>")
    .attr("for", idPrefix + plateId)
    .addClass("col-sm-5 control-label")
    .append(label)
    .appendTo($rowDiv);
  var $colDiv = $("<div>")
    .addClass("col-sm-7")
    .appendTo($rowDiv);
  var $inElem = $("<input>")
    .attr("type", "number")
    .addClass("form-control")
    .attr("id", idPrefix + plateId)
    .val(defaultValue)
    .appendTo($colDiv)
    .on("change", checksCallback)
    .attr("step", step)
    .attr("min", minVal);
  return $rowDiv;
}

function createTextInputDOM(
  $targetDiv,
  plateId,
  checksCallback,
  label,
  defaultValue,
  idPrefix
) {
  var $rowDiv = $("<div>")
    .addClass("form-group")
    .appendTo($targetDiv);
  $("<label>")
    .attr("for", idPrefix + plateId)
    .addClass("col-sm-5 control-label")
    .append(label)
    .appendTo($rowDiv);
  var $colDiv = $("<div>")
    .addClass("col-sm-7")
    .appendTo($rowDiv);
  var $inElem = $("<input>")
    .attr("type", "text")
    .addClass("form-control")
    .attr("id", idPrefix + plateId)
    .val(defaultValue)
    .appendTo($colDiv)
    .on("change", checksCallback);
  return $rowDiv;
}

function createSelectDOM(
  $targetDiv,
  plateId,
  checksCallback,
  label,
  options,
  idPrefix,
  placeholder,
  idKey
) {
  if (idKey === undefined) {
    idKey = "equipment_id";
  }
  var $rowDiv = $("<div>")
    .addClass("form-group")
    .appendTo($targetDiv);
  $("<label>")
    .attr("for", idPrefix + plateId)
    .addClass("col-sm-5 control-label")
    .append(label)
    .appendTo($rowDiv);
  var $colDiv = $("<div>")
    .addClass("col-sm-7")
    .appendTo($rowDiv);
  var $selElem = $("<select>")
    .addClass("form-control")
    .attr("plate-id", plateId)
    .attr("id", idPrefix + plateId)
    .appendTo($colDiv)
    .on("change", checksCallback);
  $("<option>")
    .prop("selected", true)
    .prop("disabled", true)
    .append(placeholder)
    .appendTo($selElem);
  $.each(options, function(idx, elem) {
    $("<option>")
      .attr("value", elem[idKey])
      .append(elem.external_id)
      .appendTo($selElem);
  });
}

function createCheckboxEnabledSpinner(
  $targetDiv,
  plateId,
  checksCallback,
  label,
  defaultValue,
  idPrefix,
  step,
  minVal
) {
  var $rowDiv = $("<div>")
    .addClass("form-group")
    .appendTo($targetDiv);
  $("<label>")
    .addClass("col-sm-5 control-label")
    .append(label)
    .appendTo($rowDiv);

  var $container = $("<div>")
    .addClass("input-group col-sm-2")
    .appendTo($rowDiv);

  // align this input-group with the rest of the form-groups
  $container.css("padding-left", "15px");
  var $addon = $("<span>")
    .addClass("input-group-addon")
    .appendTo($container);
  var $checkbox = $("<input>")
    .attr("type", "checkbox")
    .appendTo($addon);
  var $input = $("<input>")
    .attr("type", "number")
    .addClass("form-control")
    .appendTo($container)
    .on("change", checksCallback);
  $input.attr("step", step).attr("min", minVal);
  $input.attr("id", idPrefix + plateId).val(defaultValue);
  $input.prop("disabled", defaultValue === "");
  $checkbox.prop("checked", defaultValue !== "");

  // enable the input when the checkbox is checked
  $checkbox.on("change", function(element, event) {
    $input.prop("disabled", !$checkbox.prop("checked"));
    if (!$checkbox.prop("checked")) {
      $input.val(null);
    }
    checksCallback();
  });
}

function createReagentDOM(
  $targetDiv,
  plateId,
  checksCallback,
  label,
  idPrefix,
  vueTarget,
  reagentType
) {
  var $rowDiv = $("<div>")
    .addClass("form-group")
    .appendTo($targetDiv);
  $("<label>")
    .attr("for", idPrefix + plateId)
    .addClass("col-sm-5 control-label")
    .append(label)
    .appendTo($rowDiv);
  var $colDiv = $("<div>")
    .addClass("col-sm-7")
    .appendTo($rowDiv);
  var $inElem = $("<input>")
    .attr("type", "text")
    .addClass("form-control")
    .attr("id", idPrefix + plateId)
    .appendTo($colDiv);
  // Add the Vue element to the extraction kit once it has been loaded into the DOM.
  // This is needed otherwise Vue will not find the input element
  $inElem.ready(function() {
    var vueContainer = $("<div>")
      .attr("id", "vue-elem-" + idPrefix + plateId)
      .appendTo(vueTarget);
    var vueComponentCtr = Vue.extend(ReagentModalComponent);
    var vueElem = new vueComponentCtr({
      propsData: {
        idPrefix: idPrefix + plateId,
        reagentType: reagentType,
        inputTarget: idPrefix + plateId,
        checksCallback: checksCallback
      }
    });
    vueElem.$mount("#vue-elem-" + idPrefix + plateId);
  });
}

function createCheckboxDOM(
  $targetDiv,
  plateId,
  checksCallback,
  label,
  checked,
  idPrefix
) {
  var $rowDiv = $("<div>")
    .addClass("form-group")
    .appendTo($targetDiv);
  $("<label>")
    .attr("for", idPrefix + plateId)
    .addClass("col-sm-2 control-label")
    .append(label)
    .appendTo($rowDiv);
  var $colDiv = $("<div>")
    .addClass("col-sm-10")
    .appendTo($rowDiv);
  var $inElem = $("<input>")
    .attr("type", "checkbox")
    .attr("id", idPrefix + plateId)
    .prop("checked", checked)
    .appendTo($colDiv)
    .on("change", checksCallback);
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
  var value = $("#" + input)
    .val()
    .trim();
  var $div = $("#" + input).closest("div");

  if (value === "") {
    $div
      .removeClass("has-success")
      .addClass("has-error")
      .find("span")
      .removeClass("glyphicon-ok")
      .addClass("glyphicon-remove");
    $("#newNameDivMessage").text("No name specified");
  }

  if (value !== "") {
    $.get("/platename?new-name=" + value, function(data) {
      // If we get here it means that the name already exists
      $div
        .removeClass("has-success")
        .addClass("has-error")
        .find("span")
        .removeClass("glyphicon-ok")
        .addClass("glyphicon-remove");
      $("#newNameDivMessage").text("Name is already used");
      // $('#updateNameBtn').prop('disabled', true);
      checksCallback();
    }).fail(function(jqXHR, textStatus, errorThrown) {
      // We need to check the status of the response
      if (jqXHR.status === 404) {
        // The plate name doesn't exist - it is ok to change to this name
        $div
          .removeClass("has-error")
          .addClass("has-success")
          .find("span")
          .removeClass("glyphicon-remove")
          .addClass("glyphicon-ok");
        $("#newNameDivMessage").text("Name is available");
        // $('#updateNameBtn').prop('disabled', false);
        checksCallback();
        if (e.which == 13 && successCallback !== undefined) {
          // This means that the user pressed the enter key
          // so we will just call the success callback
          successCallback();
        }
      } else {
        bootstrapAlert(jqXHR.responseText, "danger");
        checksCallback();
      }
    });
  } else {
    $div
      .removeClass("has-success")
      .addClass("has-error")
      .find("span")
      .removeClass("glyphicon-ok")
      .addClass("glyphicon-remove");
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
function bootstrapAlert(message, severity, timeout) {
  $(".modal").modal("hide");
  // make timeout an optional parameter
  timeout = timeout || -1;
  // make severity an optinal parameter
  severity = typeof severity !== "undefined" ? severity : "danger";
  // Remove any previous alert message
  $("#alert-message").remove();
  // Crate the div that contains the message and append the alert message
  var alertDiv = $("<div>", {
    class: "alert fade in alert-" + severity,
    role: "alert",
    id: "alert-message"
  })
    .append('<a href="#" class="close" data-dismiss="alert">&times;</a>')
    .append(
      '<span class="glyphicon glyphicon-exclamation-sign" aria-hidden="true"></span>'
    )
    .append(message);
  // Add the alert div just under the navbar
  $("#template-content").prepend(alertDiv);
  // Set a timeout for the alert div if needed
  if (timeout > 0) {
    if (timeoutHandleForBoostrapAlert != null) {
      // This is needed in case that a new alert is generated while
      // an alert is already shown
      window.clearTimeout(timeoutHandleForBoostrapAlert);
    }
    timeoutHandleForBoostrapAlert = window.setTimeout(function() {
      $("#alert-message").remove();
      timeoutHandleForBoostrapAlert = null;
    }, timeout * 1000); // * 1000 to transform from seconds to miliseconds
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
  if (sameStrChar(u, "Z")) {
    var txt = "";
    var i = u.length;
    while (i--) {
      txt += "A";
    }
    return txt + "A";
  } else {
    var p = "";
    var q = "";
    if (u.length > 1) {
      p = u.substring(0, u.length - 1);
      q = String.fromCharCode(p.slice(-1).charCodeAt(0));
    }
    var l = u.slice(-1).charCodeAt(0);
    var z = nextLetter(l);
    if (z === "A") {
      return p.slice(0, -1) + nextLetter(q.slice(-1).charCodeAt(0)) + z;
    } else {
      return p + z;
    }
  }
}

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
    return "A";
  }
}

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

/**
 *
 **/
function addIfNotPresent(array, elem) {
  var idx = array.indexOf(elem);
  if (idx === -1) {
    array.push(elem);
  }
}

function safeArrayDelete(array, elem) {
  var idx = array.indexOf(elem);
  if (idx !== -1) {
    array.splice(idx, 1);
  }
}

/**
 * Determine an appropriate clipping value for the heatmap's maximum value.
 *
 * @param {Float} plateType String describing the plate type.
 * @returns A maximum expected value for the colorscale of a heatmap.
 *
 */
function clippingForPlateType(plateType) {
  if (plateType == "16S library prep") {
    return 100;
  } else if (plateType == "shotgun library prep") {
    return 30;
  } else if (plateType == "gDNA" || plateType == "compressed gDNA plates") {
    return 20;
  }

  // should never get here but if it does, then the range is permissive
  return 10000;
}

/**
 * Create a heatmap with well compositions and a histogram of the DNA
 * concentrations.
 *
 * The array parameters are all matched one-to-one i.e. element (2, 3) in
 * every array represents the same well in the plate.
 *
 * @param {String} plateId Element identifier for a given plate.
 * @param {Array} concentrations A 2D array of floating point values
 * representing the concentrations of a plate.
 * @param {Array} blanks A 2D array of well names.
 * @param {Float} defaultClipping A number representing the default clipping
 * value for the heatmap. Depends on the processing stage and the type of
 * data being processed.
 * @param {Object[]} options Optional parameters
 * @param {string} options[].colormap Optional colormap name for the heatmap,
 # if not provided then "YlGnBu" is used. For more information see:
 * https://matplotlib.org/users/colormaps.html
 * @param {string} options[].amounts The descriptor of the value being
 * displayed to use for annotation. If not provided, defaults to "Value"
 *
 */
function createHeatmap(
  plateId,
  concentrations,
  blanks,
  names,
  defaultClipping,
  options
) {
  var colormap = options.colormap || "YlGnBu";
  var amounts = options.amounts || "Value";

  var $container = $("#pool-results-" + plateId);

  // existing plot containers need to be removed
  $container.children().remove();

  var $heatmap = $('<div id="heatmap-' + plateId + '"></div>');
  var $histogram = $('<div id="histogram-' + plateId + '"></div>');

  $heatmap.css({ position: "relative" });

  var $spinnerContainer = $('<div name="slider-container"></div>');
  var $spinner = $('<input name="clipping-spinner" type="number">');
  var $label = $("<label>Clip values greater than</label>");
  var $resetButton = $("<button>reset</button>");

  $label.append($spinner);
  $spinnerContainer.append($label);
  $spinnerContainer.append("<br>");
  $spinnerContainer.append($resetButton);
  $spinnerContainer.css({
    width: "200px",
    height: "100px",
    position: "absolute",
    top: "0",
    left: "20px",
    "z-index": "10"
  });

  $heatmap.append($spinnerContainer);

  $container.append($heatmap);
  $container.append($histogram);

  // the arrays are reversed to have element (0, 0) at the top of the
  // heatmap, which matches the location of the wells in a physical plate
  blanks = blanks.reverse();
  concentrations = concentrations.reverse();
  names = names.reverse();

  var letters = "ABCDEFGHIJKLMPNOPQRSTUVWXYZ".split(""),
    yLabels;
  yLabels = letters.slice(0, concentrations.length);
  yLabels = yLabels.reverse();

  var minConcentration = 0;
  var hoverlabels = [],
    annotations = [],
    result;
  var flattenedBlanks = [],
    flattenedNonBlanks = [];

  // this double loop will construct the arrays necessary for the histogram
  // and the heatmap (including annotations, and legends)
  for (var i = 0; i < names.length; i++) {
    hoverlabels[i] = [];
    for (var j = 0; j < names[0].length; j++) {
      // per-well annotations on the cells, indicate with a special character
      // when the well represents a blank sample
      result = {
        x: j + 1,
        y: yLabels[i],
        text: blanks[i][j] ? "🔳" : "",
        showarrow: false
      };
      annotations.push(result);

      // per-well labels
      hoverlabels[i].push(
        "Row : " +
          yLabels[i] +
          " Column : " +
          (j + 1) +
          " <br>" +
          amounts +
          " : " +
          concentrations[i][j] +
          " <br> Sample Name : " +
          (names[i][j] == null ? "Not Available" : names[i][j])
      );

      // split the concentrations to show different colors in the histogram
      if (blanks[i][j] === true) {
        flattenedBlanks.push(concentrations[i][j]);
      } else {
        flattenedNonBlanks.push(concentrations[i][j]);
      }
    }
  }

  minConcentration = Math.min.apply(
    null,
    flattenedBlanks.concat(flattenedNonBlanks)
  );

  // setup the plotly definitions
  var heatmapData = [
    {
      x: [1],
      y: yLabels,
      z: concentrations,
      text: hoverlabels,
      hoverinfo: "text",
      type: "heatmap",
      colorscale: colormap,
      colorbar: {
        title: amounts,
        titleside: "top"
      },
      xgap: 1,
      ygap: 1,
      zmin: 0,
      zmax: defaultClipping
    }
  ];

  // make each cell a square
  var heatwidth = (600 / yLabels.length) * names[0].length;
  var heatmapLayout = {
    autosize: false,
    height: 600,
    width: heatwidth,
    xaxis: {
      autotick: false,
      side: "top"
    },
    annotations: annotations,
    title: "Per-well " + amounts
  };

  var nonBlankData = {
    name: "Non-Blank",
    x: flattenedNonBlanks,
    type: "histogram",
    marker: {
      color: "rgba(27, 158, 119, 1)",
      line: {
        color: "rgba(27, 158, 119, 1)",
        width: 5
      }
    }
  };
  var blankData = {
    name: "Blank",
    x: flattenedBlanks,
    type: "histogram",
    marker: {
      color: "rgba(217, 95, 2, 1)",
      line: {
        color: "rgba(217, 95, 2, 1)",
        width: 5
      }
    }
  };
  var histogramLayout = {
    autosize: false,
    width: heatwidth,
    xaxis: { title: amounts },
    yaxis: { title: "Number Samples" },
    title: amounts + " Distribution"
  };
  var histogramData = [nonBlankData, blankData];

  // if a plot exists with this id it should be removed
  Plotly.purge($heatmap.attr("id"));
  Plotly.purge($histogram.attr("id"));

  Plotly.plot($heatmap.attr("id"), heatmapData, heatmapLayout);
  Plotly.plot($histogram.attr("id"), histogramData, histogramLayout);

  // setup some interactivity to clip the values in the histogram
  $(function() {
    var text = "Clip values greater than ";

    // pad the minimum so the colorscale doesn't error
    $spinner.val(defaultClipping);
    $spinner.attr("min", minConcentration + 1);
    $spinner.on("input", function(a, b) {
      var clipping = parseFloat($spinner.val());
      Plotly.update($heatmap.attr("id"), { zmax: clipping }, 0);
    });

    $resetButton.on("click", function() {
      $spinner.val(defaultClipping);
      Plotly.update($heatmap.attr("id"), { zmax: defaultClipping }, 0);
    });
  });
}

/**
 *
 * Given a query string and an array of strings to search through, returns a
 * subset of the array containing only strings that contain the query string.
 *
 * This search is case insensitive, so "abc" will match with "ABCDEF".
 *
 * Note that if queryString is empty (i.e. "") then this won't return any
 * matches, even if "" is present in stringArray for some reason (since
 * stringArray should be a list of sample IDs, this should never be the case).
 *
 * This function is loosely based on textFilterFeatures() in Qurro:
 * https://github.com/biocore/qurro/blob/3f4650fb677753e978d971b06794d4790b051d30/qurro/support_files/js/feature_computation.js#L29
 *
 * @param {string} queryString The string that will be searched for
 * @param {array} stringArray Collection of strings to check against the query
 * @returns {array} Collection of strings in stringArray that include the query
 *
 */
function getSubstringMatches(queryString, stringArray) {
  if (queryString.length === 0 || stringArray.length === []) {
    return [];
  }
  var queryStringLowerCase = queryString.toLowerCase();
  var matchingStrings = [];
  for (var i = 0; i < stringArray.length; i++) {
    if (stringArray[i].toLowerCase().includes(queryStringLowerCase)) {
      matchingStrings.push(stringArray[i]);
    }
  }
  return matchingStrings;
}
