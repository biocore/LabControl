// Requires
// QUnit

// Library under test:
// addPlateModal.js

QUnit.test("populatePlateTable tests", function (assert) {
    let testPlateInfo = [
        [21, "Test plate 1",
            "2019-05-09 21:21:15.386036",
            ["Identification of the Microbiomes for Cannabis Soils"]
        ],
        [27, "Test plate 2", "2019-05-09 21:21:15.386036",
            ["Identification of the Microbiomes for Cannabis Soils"]
        ],
        [30, "Test plate 3", "2019-05-09 21:21:15.386036",
            ["Identification of the Microbiomes for Cannabis Soils"]
        ],
        [33, "Test plate 4", "2019-05-09 21:21:15.386036",
            ["Identification of the Microbiomes for Cannabis Soils"]
        ]
    ];

    function getTestElementsByName(elementName){
        return document.getElementById("qunit-fixture").
            getElementsByTagName(elementName);
    }

    insertPlateModalDiv("qunit-fixture");

    // before running function under test, table has no tbody elements
    let tbodysList = getTestElementsByName("tbody");
    assert.equal(tbodysList.length, 0);

    populatePlateTable(testPlateInfo, "#searchPlateTable",
        "addAplate");

    // after running function under test, table has 1 tbody element
    // with 4 rows
    tbodysList = getTestElementsByName("tbody");
    assert.equal(tbodysList.length, 1);
});