/**
 *
 * @class PlateViewer
 *
 * Shows the plate information
 *
 * @param {string} target The name of the target container for the plate viewer
 * @param {int} plateId OPTIONAL The id of the plate to visualize
 * @param {int} rows OPTIONAL If plateId is not provided, the number of rows
 * @param {int} cols OPTIONAL If plateId is not provided, the number of columns
 *
 * @return {PlateViewer}
 * @constructs PlateViewer
 *
 **/
function PlateViewer(target, plateId, processId, rows, cols) {
  this.container = $('#' + target);

  /*
   * HACK: SlickGrid doesn't currently support frozen columns hence we are
   * using two grids to make it look like the first column is frozen. Once
   * the feature makes it into the SlickGrid repo, we can remove this. See
   * this GitHub issue: https://github.com/6pac/SlickGrid/issues/26
   */
  this.target = $('<div name="main-grid"></div>');
  this._frozenColumnTarget = $('<div name="frozen-column" ' +
                               'class="spreadsheet-frozen-column"></div>');

  this.container.append(this._frozenColumnTarget);
  this.container.append(this.target);

  this.plateId = null;
  this.processId = null;
  this._undoRedoBuffer = null;
  this.notes = null;

  var that = this;

  if (!plateId) {
    if (!rows || !cols) {
      // This error should never show up in production
      bootstrapAlert('PlateViewer developer error: rows and cols should be provided if plateId is not provided');
    } else {
      this.initialize(rows, cols);
    }
  } else {
    // Ignore rows and cols and use the plateId to retrieve the plate
    // information and initialize the object
    this.plateId = plateId;
    this.processId = processId;
    $.get('/plate/' + this.plateId + '/', function (data) {
      var rows, cols, pcId;
      // Magic numbers. The plate configuration is a list of elements
      // Element 2 -> number of rows
      // Element 3 -> number of cols
      rows = data['plate_configuration'][2];
      cols = data['plate_configuration'][3];
      $.each(data['studies'], function (idx, elem){
        add_study(elem);
      });
      that.initialize(rows, cols);
      $.each(data['duplicates'], function(idx, elem) {
        that.wellClasses[elem[0] - 1][elem[1] - 1].push('well-duplicated');
      });
      $.each(data['previous_plates'], function(idx, elem) {
        var r = elem[0][0] - 1;
        var c = elem[0][1] - 1;
        that.wellPreviousPlates[r][c] = elem[1];
        that.wellClasses[r][c].push('well-prev-plated');
      });
      $.each(data['unknowns'], function(idx, elem) {
        that.wellClasses[elem[0] - 1][elem[1] - 1].push('well-unknown');
      });
      that.loadPlateLayout();
    })
      .fail(function (jqXHR, textStatus, errorThrown) {
        bootstrapAlert(jqXHR.responseText, 'danger');
      });
  }
};

/**
 *
 * Initializes SlickGrid to show the plate layout
 *
 * @param {int} rows The number of rows
 * @param {int} cols The number of columns
 *
 **/
PlateViewer.prototype.initialize = function (rows, cols) {
  var that = this;
  var height = '250px';

  this.rows = rows;
  this.cols = cols;
  this.data = [];
  this.frozenData = [];
  this.wellComments = [];
  this.wellPreviousPlates = [];
  this.wellClasses = [];

  // Make sure all rows fit on screen. we need to have enough space so that we
  // don't have to synchronize the scrolling events between the two elements
  if (rows > 8) {
    height = '450px';
  }
  this.container.height(height);
  this.target.height(height);
  this._frozenColumnTarget.height(height);

  var sgOptions = {editable: true,
                   enableCellNavigation: true,
                   asyncEditorLoading: false,
                   enableColumnReorder: false,
                   autoEdit: true,
                   resizable: true};

  var frozenColumnOptions = {editable: false,
                             enableCellNavigation: false,
                             enableColumnReorder: false,
                             autoEdit: false};

  // Use the slick-header-column but with mouse events disabled
  // Without the &nbsp; the header will be smaller than for the main grid
  var frozenColumn = [{id: 'selector',
                       name: '&nbsp;',
                       field: 'header',
                       width: 22,
                       cssClass: 'slick-header-column',
                       headerCssClass: 'full-height-header'}];

  // Fetch the blank names before initializing the grid. This way we only make
  // one request to get this data instead of one per cell instantiation.
  // When no search term is specified in the request, we get all available
  // blank types.
  var blanksRequest = $.get({
    dataType: 'json',
    url: '/sample/control?term=',
    error: function(jqXHR, textStatus, errorThrown) {
     bootstrapAlert('Could not fetch known <i>Control Types</i> needed for ' +
                    'plating samples. Try reloading the page. <br>' +
                    jqXHR.responseText, 'danger');
    }
  });

  var sgCols = [];

  for (var i = 0; i < this.cols; i++) {
    // We need to add the plate Viewer as an element of this list so it gets
    // available in the formatter.
    sgCols.push({
      plateViewer: this,
      id: i,
      name: i+1,
      field: i,
      editor: SampleCellEditor,
      options: {'blankNamesRequest': blanksRequest},
      formatter: this.wellFormatter,
      width:100,
      minWidth: 80,
      headerCssClass: 'full-height-header'});
  }
  var rowId = 'A';

  for (var i = 0; i < this.rows; i++) {
    var d = (this.data[i] = {});
    var c = (this.wellComments[i] = {});
    var cl = (this.wellClasses[i] = {});
    var pp = (this.wellPreviousPlates[i] = {});

    this.frozenData.push({'header': rowId});

    for (var j = 0; j < this.cols; j++) {
      d[j] = null;
      c[j] = null;
      cl[j] = [];
      pp[j] = null;
    }
    rowId = getNextRowId(rowId);
  }


  /*
   * Taken from the example here:
   * https://github.com/6pac/SlickGrid/blob/master/examples/example-excel-compatible-spreadsheet.html
   */
  this._undoRedoBuffer = {
      commandQueue : [],
      commandCtr : 0,
      queueAndExecuteCommand : function(editCommand) {
        this.commandQueue[this.commandCtr] = editCommand;
        this.commandCtr++;
        editCommand.execute();
      },
      undo : function() {
        if (this.commandCtr == 0) {
          return;
        }
        this.commandCtr--;
        var command = this.commandQueue[this.commandCtr];
        if (command && Slick.GlobalEditorLock.cancelCurrentEdit()) {
          command.undo();
        }
      },
      redo : function() {
        if (this.commandCtr >= this.commandQueue.length) { return; }
        var command = this.commandQueue[this.commandCtr];
        this.commandCtr++;
        if (command && Slick.GlobalEditorLock.cancelCurrentEdit()) {
          command.execute();
        }
      }
  };

  var sgOptions = {
    editable: true,
    enableCellNavigation: true,
    asyncEditorLoading: false,
    enableColumnReorder: false,
    autoEdit: true,
    editCommandHandler: function(item, column, editCommand) {
     that._undoRedoBuffer.queueAndExecuteCommand(editCommand);
    }
  };

  // Handle the callbacks to CTRL + Z and CTRL + SHIFT + Z
  $(document).keydown(function(e)
  {
    if (e.which == 90 && (e.ctrlKey || e.metaKey)) {    // CTRL + (shift) + Z
      if (e.shiftKey){
        that._undoRedoBuffer.redo();
      } else {
        that._undoRedoBuffer.undo();
      }
    }
    // ESC enters selection mode, so autoEdit should be turned off to allow
    // users to navigate between cells with the arrow keys
    if (e.keyCode === 27) {
      that.grid.setOptions({autoEdit: false});
    }
  });

  var pluginOptions = {
    clipboardCommandHandler: function(editCommand){
      that._undoRedoBuffer.queueAndExecuteCommand.call(that._undoRedoBuffer,editCommand);
    },
    readOnlyMode : false,
    includeHeaderWhenCopying : false
  };

  this._frozenColumn = new Slick.Grid(this._frozenColumnTarget, this.frozenData,
                                      frozenColumn, frozenColumnOptions);
  this.grid = new Slick.Grid(this.target, this.data, sgCols, sgOptions);

  // don't select the active cell, otherwise cell navigation won't work
  this.grid.setSelectionModel(new Slick.CellSelectionModel({selectActiveCell: false}));
  this.grid.registerPlugin(new Slick.CellExternalCopyManager(pluginOptions));

  // When a cell changes, update the server with the new cell information
  this.grid.onCellChange.subscribe(function(e, args) {
    var row = args.row;
    var col = args.cell;
    var content = args.item[col];

    // The plate already exists, simply plate the sample
    that.modifyWell(row, col, content);
  });

  // When the user right-clicks on a cell
  this.grid.onContextMenu.subscribe(function(e) {
    e.preventDefault();
    var cell = that.grid.getCellFromEvent(e);
    $('#wellContextMenu').data('row', cell.row).data('col', cell.cell).css('top', e.pageY).css('left', e.pageX).show();
    $('body').one('click', function() {
      $('#wellContextMenu').hide();
    })
  });

  // Add the functionality to the context menu
  $('#wellContextMenu').click(function (e) {
    if (!$(e.target).is("li")) {
      return;
    }
    if(!that.grid.getEditorLock().commitCurrentEdit()){
      return;
    }
    var row = $(this).data("row");
    var col = $(this).data("col");
    var func = $(e.target).attr("data");

    // Set up the modal to add a comment to the well
    $('#addWellCommentBtn').off('click');
    $('#addWellCommentBtn').on('click', function(){
      that.commentWell(row, col, $('#wellTextArea').val());
    });

    $('#wellTextArea').val(that.wellComments[row][col]);

    // Set the previous comment in the input
    // Show the modal
    $('#addWellComment').modal('show');
  });
};

PlateViewer.prototype.wellFormatter = function (row, col, value, columnDef, dataContext) {

  var spanId = 'well-' + row + '-' + col;
  var classes = '';
  // For some reason that goes beyond my knowledge, although this function
  // is part of the PlateViewer class, when accessing to "this" I do not retrieve
  // the plateViewer object. SlickGrid must be calling it in a weird way
  var vp = columnDef.plateViewer;
  if (vp.wellClasses[row][col].length > 0) {
    classes = ' class="' + vp.wellClasses[row][col][0];
    for (var i = 1; i < vp.wellClasses[row][col].length; i++) {
      classes = classes + ' ' + vp.wellClasses[row][col][i];
    }
    classes = classes + '"';
  }
  if (value === null) {
    value = '';
  }
  return '<span id="' + spanId + '"' + classes + '>' + value + '</span>';
};

/**
 *
 * Loads the plate layout in the current grid
 *
 **/
PlateViewer.prototype.loadPlateLayout = function () {
  var that = this;

  $.get('/plate/' + this.plateId + '/layout', function (data) {
    // Update the Grid data with the received information
    data = $.parseJSON(data);
    that.grid.invalidateAllRows();
    for (var i = 0; i < that.rows; i++) {
      for (var j = 0; j < that.cols; j++) {
        that.data[i][j] = data[i][j]['sample'];
        that.wellComments[i][j] = data[i][j]['notes'];
        if (that.wellComments[i][j] !== null) {
          that.wellClasses[i][j].push('well-commented');
        }
      }
    }
    that.grid.render();
    that.updateWellCommentsArea();
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      bootstrapAlert(jqXHR.responseText, 'danger');
    });
};

/**
 * Fetch the study that is currently selected in the UI.
 * If there is NO selected study in the UI, then the
 * method returns 0 (which is not a valid study id).
 * This special non-valid value is checked for in the
 * back end (in sample_plating_process_handler_patch_request)
 * so do not change here without changing there.
 */
PlateViewer.prototype.getActiveStudy = function () {
  studyID = get_active_studies().pop();

  if (studyID === undefined) {
    return 0;
  }
  return studyID;
};

/**
 *
 * Modify the contents of a well
 *
 * @param {int} row The row of the well being modified
 * @param {int} col The column of the well being modified
 * @param {string} content The new content of the well
 *
 **/
PlateViewer.prototype.modifyWell = function (row, col, content) {
  var that = this, studyID = this.getActiveStudy();

  $.ajax({url: '/process/sample_plating/' + this.processId,
         type: 'PATCH',
         data: {'op': 'replace', 'path': '/well/' + (row + 1) + '/' + (col + 1) + '/' + studyID + '/sample', 'value': content},
         success: function (data) {

           that.data[row][that.grid.getColumns()[col].field] = data['sample_id'];
           that.updateUnknownsAndDuplicates();
           var classIdx = that.wellClasses[row][col].indexOf('well-prev-plated');
           if (data['previous_plates'].length > 0) {
             that.wellPreviousPlates[row][col] = data['previous_plates'];
             addIfNotPresent(that.wellClasses[row][col], 'well-prev-plated');
           } else {
             safeArrayDelete(that.wellClasses[row][col], 'well-prev-plated');
             that.wellPreviousPlates[row][col] = null;
           }

           // here and in the rest of the source we use updateRow instead of
           // invalidateRow(s) and render so that we don't lose any active
           // editors in the current grid
           that.grid.updateRow(row);
           that.updateWellCommentsArea();
         },
         error: function (jqXHR, textStatus, errorThrown) {
           bootstrapAlert(jqXHR.responseText, 'danger');
         }
  });
};

/**
**/
PlateViewer.prototype.commentWell = function (row, col, comment) {
  var that = this, studyID = this.getActiveStudy();

  $.ajax({url: '/process/sample_plating/' + this.processId,
         type: 'PATCH',
         data: {'op': 'replace', 'path': '/well/' + (row + 1) + '/' + (col + 1) + '/' + studyID + '/notes', 'value': comment},
         success: function (data) {
           that.wellComments[row][col] = data['comment'];
           var classIdx = that.wellClasses[row][col].indexOf('well-commented');
           if (data['comment'] === null && classIdx > -1) {
             that.wellClasses[row][col].splice(classIdx, 1);
           } else if (data['comment'] !== null && classIdx === -1) {
             that.wellClasses[row][col].push('well-commented')
           }

           that.grid.updateRow(row);

           // Close the modal
           $('#addWellComment').modal('hide');
           that.updateWellCommentsArea();
         },
         error: function (jqXHR, textStatus, errorThrown) {
           bootstrapAlert(jqXHR.responseText, 'danger');
         }
  });
};

/**
 * Update the contents of the grid
 *
 * This method is mainly motivated by updateUnknownsAndDuplicates,
 * which may need to update cells that were not recently updated.
 *
 * Here and in the rest of the source we use updateRow instead of
 * invalidateRows and render so that we don't lose any active editors in the
 * current grid
 *
 */
PlateViewer.prototype.updateAllRows = function () {
  for (var i = 0; i < this.rows; i ++ ) {
    this.grid.updateRow(i);
  }
};


PlateViewer.prototype.updateUnknownsAndDuplicates = function () {
  var that = this;

  var successFunction = function (data) {
    var classIdx;
    // First remove all the instances of the unknown and duplicated css classes from  wells
    for (var i = 0; i < that.rows; i++) {
      for (var j = 0; j < that.cols; j++) {
        safeArrayDelete(that.wellClasses[i][j], 'well-unknown');
        safeArrayDelete(that.wellClasses[i][j], 'well-duplicated');
      }
    }
    // Add the unknown class to all the current unknowns
    $.each(data['unknowns'], function(idx, elem) {
      var row = elem[0] - 1;
      var col = elem[1] - 1;
      that.wellClasses[row][col].push('well-unknown');
    });

    // Add the duplicated class to all the current duplicates
    $.each(data['duplicates'], function(idx, elem) {
      var row = elem[0] - 1;
      var col = elem[1] - 1;
      that.wellClasses[row][col].push('well-duplicated');
    });

    that.updateAllRows();
  };

  $.ajax({
      url: '/plate/' + this.plateId + '/',
      dataType: "json",
      // A value of 0 means there will be no timeout.
      // from https://api.jquery.com/jquery.ajax/#jQuery-ajax-settings
      timeout: 0,
      success: successFunction,
      error: function (jqXHR, textStatus, errorThrown) {
        bootstrapAlert(jqXHR.responseText, 'danger');
      }
  });
};

PlateViewer.prototype.updateWellCommentsArea = function () {
  var that = this;
  var msg;
  $('#well-plate-comments').empty();
  var rowId = 'A';
  var wellId;
  for (var i = 0; i < that.rows; i++) {
    for (var j = 0; j < that.cols; j++) {
      wellId = rowId + (j + 1);
      if(that.wellComments[i][j] !== null) {
        msg = 'Well ' + wellId + ' (' + that.data[i][j] + '): ' + that.wellComments[i][j];
        $('<p>').append(msg).appendTo('#well-plate-comments');
      } else if (that.wellPreviousPlates[i][j] !== null){
        msg = 'Well ' + wellId + ' (' + that.data[i][j] + '): Plated in :';
        $.each(that.wellPreviousPlates[i][j], function(idx, elem) {
          msg = msg + ' "' + elem['plate_name'] + '"'
        });
        $('<p>').addClass('well-prev-plated').append(msg).appendTo('#well-plate-comments');
      }
    }
    rowId = getNextRowId(rowId);
  }
};

/**
 *
 * @class SampleCellEditor
 *
 * This class represents a Sample cell editor defined by the SlickGrid project
 *
 * This is heavily based on SlickGrid's TextEditor
 * (https://github.com/6pac/SlickGrid/blob/master/slick.editors.js)
 * And the SlickGrid's example of autocomplete:
 * (https://github.com/6pac/SlickGrid/blob/master/examples/example-autocomplete-editor.html)
 *
 * @param {Object} args Arguments passed by SlickGrid
 *
 **/
function SampleCellEditor(args) {
  var $input;
  var defaultValue;
  var that = this;

  // Do not use the up and down arrow to navigate the cells so they can be used
  // to choose the sample from the autocomplete dropdown menu
  this.keyCaptureList = [Slick.keyCode.UP, Slick.keyCode.DOWN];

  // Get the parsed values from the request. Alternatively, if the request
  // didn't complete yet use an empty list as a fallback.
  this.blankNames = args.column.options.blankNamesRequest.responseJSON || [];

  // styling taken from SlickGrid's examples/examples.css file
  this.init = function () {
    $input = $("<input type='text'>")
        .appendTo(args.container)
        .on("keydown.nav", function (e) {
          if (e.keyCode === $.ui.keyCode.LEFT || e.keyCode === $.ui.keyCode.RIGHT) {
            e.stopImmediatePropagation();
          }
        })
        .css({'width': '100%',
              'height':'100%',
              'border':'0',
              'margin':'0',
              'background': 'transparent',
              'outline': '0',
              'padding': '0'});

    $input.autocomplete({source: autocomplete_search_samples});

    args.grid.setOptions({autoEdit: true});
  };

  this.destroy = function () {
    $input.remove();
  };

  this.focus = function () {
    $input.focus();
  };

  this.getValue = function () {
    return $input.val();
  };

  this.setValue = function (val) {
    $input.val(val);
  };

  this.loadValue = function (item) {
    defaultValue = item[args.column.field] || "";
    $input.val(defaultValue);
    $input[0].defaultValue = defaultValue;
    $input.select();
  };

  this.serializeValue = function () {
    return $input.val();
  };

  this.applyValue = function (item, state) {
    var activeStudies, studyPrefix = '';

    // account for the callback when copying or pasting
    if (state === null) {
      state = '';
    }
    
    if (state.replace(/\s/g,'').length === 0) {
      // The user introduced an empty string. An empty string in a plate is a blank
      state = 'blank';
    }

    item[args.column.field] = state;
  };

  this.isValueChanged = function () {
    return (!($input.val() == "" && defaultValue == null)) && ($input.val() != defaultValue);
  };

  this.validate = function () {
    if (args.column.validator) {
      var validationResults = args.column.validator($input.val());
      if (!validationResults.valid) {
        return validationResults;
      }
    }

    return {
      valid: true,
      msg: null
    };
  };

  this.init();
}

/**
 *
 * Function to fill up the autocomplete dropdown menu for the samples
 *
 * @param {object} request Request object sent by JQuery UI autocomple
 * @param {function} response Callback function sent by JQuery UI autocomplete
 *
 **/
function autocomplete_search_samples(request, response) {
  // Check if there is any study chosen
  var studyIds = get_active_studies();

  // Perform all the requests to the server
  var requests = [$.get('/sample/control?term=' + request.term)];
  $.each(studyIds, function (index, value) {
    requests.push($.get('/study/' + value + '/samples?term=' + request.term));
  });

  $.when.apply($, requests).then(function () {
    // The nature of arguments change based on the number of requests performed
    // If only one request was performed, then arguments only contain the output
    // of that request. On the other hand, if there was more than one request,
    // then arguments is a list of results
    var arg = (requests.length === 1) ? [arguments] : arguments;
    var samples = [];
    $.each(arg, function(index, value) {
      samples = samples.concat($.parseJSON(value[0]));
    });
    // Format the samples in the way that autocomplete needs
    var results = [];
    $.each(samples, function(index, value) {
      results.push({'label': value, 'value': value});
    });
    response(results);
  });
}

/**
 * Function to retrieve the selected studies from the UI
 * @returns {Array} A list of study identifiers that are currently selected.
 */
function get_active_studies() {
  var $studies = $('.study-list-item.active');
  var studyIds = [];

  if ($studies.length === 0) {
    // There are no studies chosen - search over all studies in the list:
    $.each($('.study-list-item'), function (index, value) {
      studyIds.push($(value).attr('pm-data-study-id'));
    });
  } else {
    $.each($studies, function (index, value) {
      studyIds.push($(value).attr('pm-data-study-id'));
    });
  }

  return studyIds;
}


/**
 * Small widget to add notes and save them to a URI
 *
 * @param {Node} container The HTML container where the widget will be appended
 * to.
 * @param {String} uri The route where the data is written to.
 * @param {Integer} id The process identifier for the uri.
 * @param {Object} options Object with custom parameters to modify the
 * behaviour of the widget.
 */
function NotesBox(container, uri, id, options) {
  var that = this;
  options = options || {};

  this.title = options.title || 'Notes';
  this.placeholder = options.placeholder || 'Enter your notes and click ' +
                                            'the save button';
  this.text = '';
  this.uri = uri;
  this.id = id;
  this.$container = $(container);

  this.$main = $('<div></div>').addClass('form-group').width('100%');
  this.$container.append(this.$main);

  this.$label = $('<label></label>').width('100%');
  this.$textArea = $('<textarea class="form-control"></textarea>');
  this.$textArea.css({width: '100%'});
  this.$saveButton = $('<button type="button">Save Notes</button>');
  this.$saveButton.addClass('btn btn-primary');

  this.$label.html(this.title);
  this.$label.append(this.$textArea);

  this.$main.append(this.$label);
  this.$main.append(this.$saveButton);

  this.$textArea.on('input', function() {
    that.$saveButton.removeClass('btn-primary btn-danger btn-success');
    that.$saveButton.addClass('btn-primary');
    that.$saveButton.html('Save Notes');
    that.text = that.$textArea.val();
  });

  this.$textArea.attr('placeholder', this.placeholder);

  this.$saveButton.on('click', function() {
    that.save();
    $(this).addClass('disabled');
  });
}

/**
 * Method to set the text value to the object.
 *
 * @param {String} text The text you want set in the NotesBox.
 * @param {Bool} save Whether or not the text should be saved to the server.
 * Useful when preloading text into the UI. Default is False.
 */
NotesBox.prototype.setText = function(text, save) {
  this.text = text;
  this.$textArea.val(text);

  if (save) {
    this.save();
  }
};

/**
 * Method to write the notes into the uri.
 */
NotesBox.prototype.save = function () {
  var that = this;

  $.ajax({
    type: 'POST',
    url: this.uri,
    data: {process_id: this.id, notes: this.text},
  })
  .done(function() {
      that.$saveButton.removeClass('disabled btn-primary btn-danger btn-success');
      that.$saveButton.addClass('btn-success');

      that.$saveButton.html('Save Notes (successfully saved)');
    })
  .fail(function() {
      that.$saveButton.removeClass('disabled btn-primary btn-danger btn-success');
      that.$saveButton.addClass('btn-danger');

      that.$saveButton.html('Save Notes (error, try again)');
    });
};
