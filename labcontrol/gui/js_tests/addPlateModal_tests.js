// Requires
// QUnit

// Library under test:
// addPlateModal.js

// Tests of function insertPlateModalDiv
QUnit.module("insertPlateModalDiv", function (hooks) {
    // Verify correct behavior using default arguments
    QUnit.test("default arguments", function (assert) {
        //jquery selector strings
        let modalIdDivSelectorStr = "body div#addPlateModal";
        let tableIdSelectorStr = "body table#searchPlateTable";

        // before running function under test, body has no div with
        // default modal id and no table with default table name
        assert.equal($(modalIdDivSelectorStr).length, 0);
        assert.equal($(tableIdSelectorStr).length, 0);

        insertPlateModalDiv();

        // after running function under test, table has these elements
        assert.equal($(modalIdDivSelectorStr).length, 1);
        assert.equal($(tableIdSelectorStr).length, 1);

        // NOTE: unlike python unit tests, qunit does not abort the whole
        // test case when an assert fails.  Therefore, the cleanup can
        // simply be done in-line at the end of the test.
        // Also note that this clean-up can't be done automatically as the dom
        // objects were added (intentionally) to body rather than to the
        // qunit-fixture div.
        $(modalIdDivSelectorStr).remove();
    });

    // Verify correct behavior when arguments are explicitly specified
    QUnit.test("explicit arguments", function (assert) {
        //explicit names
        let modalId = 'myModal';
        let tableId = 'myPlateTable';
        let parentId = 'qunit-fixture';

        //jquery selector strings
        let modalIdDivSelectorStr = "#" + parentId + " div#" + modalId;
        let tableIdSelectorStr = "#" + parentId + " table#" + tableId;

        // before running function under test, qunit-fixture has no div
        // with explicit modal id and no table with explicit table name
        assert.equal($(modalIdDivSelectorStr).length, 0);
        assert.equal($(tableIdSelectorStr).length, 0);

        insertPlateModalDiv(parentId, modalId, tableId);

        // after running function under test, table has these elements
        assert.equal($(modalIdDivSelectorStr).length, 1);
        assert.equal($(tableIdSelectorStr).length, 1);
    });
});

// QUnit.module("getPlateListPromise", function (hooks) {
//     QUnit.test("default arguments", function (assert) {
//         let obs = getPlateListPromise(['gDNA'], false);
//         let exp = 'yah!';
//         assert.equal(Object.keys(obs), exp);
//     });
// });

// Tests of functions that depend on the plate modal div having already
// been inserted
QUnit.module("modal-div-dependent tests", function (hooks) {
    hooks.beforeEach(function (assert) {
        insertPlateModalDiv("qunit-fixture");
    });

    // No need for an afterEach hook because the modal div is inserted into
    // the qunit-fixture div, which QUnit automatically empties after each test

    // Tests of the function populatePlateTable
    QUnit.module("populatePlateTable", function (hooks) {
        let qunitTbodySelectorStr = "#qunit-fixture tbody";

        // Verify correct behavior when some realistic plates are input
        QUnit.test("happy path", function (assert) {
            let tbodyInnerHtml = '<tr role="row" class="odd"><td ' +
                'class="sorting_1">33</td><td>Test plate 4</td><' +
                'td>2019-05-09 21:21:15.386036</td>' +
                '<td>Identification of the Microbiomes for ' +
                'Cannabis Soils</td><td><button id="addAplate33" ' +
                'class="btn btn-success btn-circle-small">' +
                '<span class="glyphicon glyphicon-plus"></span>' +
                '</button></td></tr><tr role="row" class="even">' +
                '<td class="sorting_1">30</td><td>Test plate 3</td>' +
                '<td>2019-05-09 21:21:15.386036</td><td>Identification ' +
                'of the Microbiomes for Cannabis Soils</td><td>' +
                '<button id="addAplate30" class="btn btn-success ' +
                'btn-circle-small"><span class="glyphicon ' +
                'glyphicon-plus"></span></button></td></tr>' +
                '<tr role="row" class="odd">' +
                '<td class="sorting_1">27</td><td>Test plate 2</td><' +
                'td>2019-05-09 21:21:15.386036</td>' +
                '<td>Identification of the Microbiomes for Cannabis ' +
                'Soils<br>Some other study</td><td><button id="addAplate27" ' +
                'class="btn btn-success btn-circle-small">' +
                '<span class="glyphicon glyphicon-plus"></span></button>' +
                '</td></tr><tr role="row" class="even">' +
                '<td class="sorting_1">21</td><td>Test plate 1</td>' +
                '<td>2019-05-09 21:21:15.386036</td>' +
                '<td>Identification of the Microbiomes for Cannabis ' +
                'Soils</td><td><button id="addAplate21" ' +
                'class="btn btn-success btn-circle-small"><' +
                'span class="glyphicon glyphicon-plus"></span></button>' +
                '</td></tr>';
            let testPlateInfo = [
                [21, "Test plate 1",
                    "2019-05-09 21:21:15.386036",
                    ["Identification of the Microbiomes for Cannabis Soils"]
                ],
                [27, "Test plate 2", "2019-05-09 21:21:15.386036",
                    ["Identification of the Microbiomes for Cannabis Soils",
                    "Some other study"]
                ],
                [30, "Test plate 3", "2019-05-09 21:21:15.386036",
                    ["Identification of the Microbiomes for Cannabis Soils"]
                ],
                [33, "Test plate 4", "2019-05-09 21:21:15.386036",
                    ["Identification of the Microbiomes for Cannabis Soils"]
                ]
            ];

            // before running function under test, table has no tbody elements
            assert.equal($(qunitTbodySelectorStr).length, 0);

            populatePlateTable(testPlateInfo, "#searchPlateTable",
                "addAplate");

            // after running function under test, table has 1 tbody element
            // containing rows for 4 plates
            let tbodysList = $($(qunitTbodySelectorStr));
            assert.equal(tbodysList.length, 1);
            assert.equal(tbodysList[0].innerHTML, tbodyInnerHtml)
        });

        // Verify correct behavior when no plates are input
        QUnit.test("no plates", function (assert) {
            let tbodyInnerHtml = '<tr class="odd"><td valign="top" ' +
                'colspan="5" class="dataTables_empty">No data available in ' +
                'table</td></tr>';

            // before running function under test, table has no tbody elements
            assert.equal($(qunitTbodySelectorStr).length, 0);

            populatePlateTable([], "#searchPlateTable", "addAplate");

            // after running function under test, table has 1 tbody element
            // containing a row saying there are no records
            let tbodysList = $($(qunitTbodySelectorStr));
            assert.equal(tbodysList.length, 1);
            assert.equal(tbodysList[0].innerHTML, tbodyInnerHtml)
        });
    });
});


