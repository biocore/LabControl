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
  this.target = $('#' + target);
  this.plateId = null;
  this.processId = null;

  this._undoRedoBuffer = null;

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
  this.rows = rows;
  this.cols = cols;
  this.data = [];
  this.wellComments = [];
  this.wellPreviousPlates = [];
  this.wellClasses = [];

  var sgCols = [{id: 'selector', name: '', field: 'header', width: 30}]
  for (var i = 0; i < this.cols; i++) {
    // We need to add the plate Viewer as an element of this list so it gets
    // available in the formatter.
    sgCols.push({plateViewer: this, id: i, name: i+1, field: i, editor: SampleCellEditor, formatter: this.wellFormatter});
  }
  var rowId = 'A';
  for (var i = 0; i < this.rows; i++) {
    var d = (this.data[i] = {});
    var c = (this.wellComments[i] = {});
    var cl = (this.wellClasses[i] = {});
    var pp = (this.wellPreviousPlates[i] = {});
    d["header"] = rowId;
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
        if (this.commandCtr == 0) { return; }
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

  this.grid = new Slick.Grid(this.target, this.data, sgCols, sgOptions);

  // don't select the active cell, otherwise cell navigation won't work
  this.grid.setSelectionModel(new Slick.CellSelectionModel({selectActiveCell: false}));
  this.grid.registerPlugin(new Slick.CellExternalCopyManager(pluginOptions));

  // When a cell changes, update the server with the new cell information
  this.grid.onCellChange.subscribe(function(e, args) {
    var row = args.row;
    // In the GUI, the first column correspond to the row header, hence we have
    // to substract one to get the correct column index
    var col = args.cell - 1;
    var content = args.item[col];

    if (that.plateId == null) {
      // This is a new plate, we need to create the plate
      var plateName = $('#newNameInput').val().trim();
      var plateConf = $('#plate-conf-select option:selected').val();
      $.post('/process/sample_plating', {'plate_name': plateName, 'plate_configuration': plateConf}, function (data) {
        that.plateId = data['plate_id'];
        that.processId = data['process_id'];
        $('#plateName').prop('pm-data-plate-id', that.plateId);
        $('#plateName').prop('pm-data-process-id', that.processId);
        // Once the plate has been created, we can disable the plate config select
        $('#plate-conf-select').prop('disabled', true);
        // The plate has been created, plate the sample
        that.modifyWell(row, col, content);
      })
        .fail(function (jqXHR, textStatus, errorThrown) {
          bootstrapAlert(jqXHR.responseText, 'danger');
        });
    } else {
      // The plate already exists, simply plate the sample
      that.modifyWell(row, col, content);
    }
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
    // col - 1 to get the correct index, since column 0 is the header
    // in the actual slickgrid
    var col = $(this).data("col") - 1;
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
  // Correct the index
  col = col - 1;
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
}

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
 *
 * Modify the contents of a well
 *
 * @param {int} row The row of the well being modified
 * @param {int} col The column of the well being modified
 * @param {string} content The new content of the well
 *
 **/
PlateViewer.prototype.modifyWell = function (row, col, content) {
  var that = this;
  $.ajax({url: '/process/sample_plating/' + this.processId,
         type: 'PATCH',
         data: {'op': 'replace', 'path': '/well/' + (row + 1) + '/' + (col + 1) + '/sample', 'value': content},
         success: function (data) {
           that.grid.invalidateRow(row);
           that.data[row][that.grid.getColumns()[col + 1].field] = data['sample_id'];
           that.updateDuplicates();
           that.updateUnknown();
           var classIdx = that.wellClasses[row][col].indexOf('well-prev-plated');
           if (data['previous_plates'].length > 0) {
             that.wellPreviousPlates[row][col] = data['previous_plates'];
             addIfNotPresent(that.wellClasses[row][col], 'well-prev-plated');
           } else {
             safeArrayDelete(that.wellClasses[row][col], 'well-prev-plated');
             that.wellPreviousPlates[row][col] = null;
           }
           that.updateWellCommentsArea();
           that.grid.render();
         },
         error: function (jqXHR, textStatus, errorThrown) {
           bootstrapAlert(jqXHR.responseText, 'danger');
         }
  });
}

/**
**/
PlateViewer.prototype.commentWell = function (row, col, comment) {
  var that = this;
  $.ajax({url: '/process/sample_plating/' + this.processId,
         type: 'PATCH',
         data: {'op': 'replace', 'path': '/well/' + (row + 1) + '/' + (col + 1) + '/notes', 'value': comment},
         success: function (data) {
           that.wellComments[row][col] = data['comment'];
           var classIdx = that.wellClasses[row][col].indexOf('well-commented');
           if (data['comment'] === null && classIdx > -1) {
             that.wellClasses[row][col].splice(classIdx, 1);
           } else if (data['comment'] !== null && classIdx === -1) {
             that.wellClasses[row][col].push('well-commented')
           }
           that.grid.invalidateRow(row);
           that.grid.render();
           // Close the modal
           $('#addWellComment').modal('hide');
           that.updateWellCommentsArea();
         },
         error: function (jqXHR, textStatus, errorThrown) {
           bootstrapAlert(jqXHR.responseText, 'danger');
         }
  });
}

PlateViewer.prototype.updateDuplicates = function () {
  var that = this;
  $.get('/plate/' + this.plateId + '/', function (data) {
    var classIdx;
    // First remove all the instances of the duplicated wells
    for (var i = 0; i < that.rows; i++) {
      for (var j = 0; j < that.cols; j++) {
        safeArrayDelete(that.wellClasses[i][j], 'well-duplicated');
      }
    }
    // Add the class to all the duplicates
    $.each(data['duplicates'], function(idx, elem) {
      var row = elem[0] - 1;
      var col = elem[1] - 1;
      that.wellClasses[row][col].push('well-duplicated');
      that.data[row][col] = elem[2];
    });

    that.grid.invalidateAllRows();
    that.grid.render();
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      bootstrapAlert(jqXHR.responseText, 'danger');
    });
};

PlateViewer.prototype.updateUnknown = function () {
  var that = this;
  $.get('/plate/' + this.plateId + '/', function (data) {
    var classIdx;
    // First remove all the instances of the unknown wells
    for (var i = 0; i < that.rows; i++) {
      for (var j = 0; j < that.cols; j++) {
        safeArrayDelete(that.wellClasses[i][j], 'well-unknown');
      }
    }
    // Add the class to all the duplicates
    $.each(data['unknowns'], function(idx, elem) {
      var row = elem[0] - 1;
      var col = elem[1] - 1;
      that.wellClasses[row][col].push('well-unknown');
    });

    that.grid.invalidateAllRows();
    that.grid.render();
  })
    .fail(function (jqXHR, textStatus, errorThrown) {
      bootstrapAlert(jqXHR.responseText, 'danger');
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
  var scope = this;

  // Do not use the up and down arrow to navigate the cells so they can be used
  // to choose the sample from the autocomplete dropdown menu
  this.keyCaptureList = [Slick.keyCode.UP, Slick.keyCode.DOWN];

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
    // account for the callback when copying or pasting
    if (state === null) {
      state = '';
    }
    var content = state.replace(/\s/g,'');
    if (content.length === 0) {
      // The user introduced an empty string. An empty string in a plate is a blank
      state = 'blank';
    }
    // Replace all non-alpha numeric characters by '.'
    state = state.replace(/[^a-z0-9]/gmi, ".");
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
};

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
