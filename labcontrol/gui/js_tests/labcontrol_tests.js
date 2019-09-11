// Requires
// QUnit

// Library under test:
// labcontrol.js

// Tests of getNextRowId function
QUnit.module("getNextRowId", function(hooks) {
  QUnit.test("increment last letter", function(assert) {
    assert.equal(getNextRowId("A"), "B");
    assert.equal(getNextRowId("M"), "N");
    assert.equal(getNextRowId("X"), "Y");
    assert.equal(getNextRowId("ABC"), "ABD");
    assert.equal(getNextRowId("abc"), "ABD");
  });
  QUnit.test("increment number of letters", function(assert) {
    assert.equal(getNextRowId("Z"), "AA");
    assert.equal(getNextRowId("ZZ"), "AAA");
    assert.equal(getNextRowId("ZX"), "ZY");
    assert.equal(getNextRowId("ABZ"), "ACA");
  });
});

// Tests of nextLetter function
QUnit.module("nextLetter", function(hooks) {
  QUnit.test("typical alphabet", function(assert) {
    assert.equal(nextLetter(64), "A");
    assert.equal(nextLetter(65), "B");
    assert.equal(nextLetter(89), "Z");
  });
  QUnit.test("special characters", function(assert) {
    assert.equal(nextLetter(90), "A");
    assert.equal(nextLetter(99), "A");
  });
});

// Tests of sameStrChar function
QUnit.module("sameStrChar", function(hooks) {
  QUnit.test("common usage", function(assert) {
    assert.ok(sameStrChar("AAA", "A"));
    assert.ok(sameStrChar("ZZZ", "Z"));
    assert.notOk(sameStrChar("ABC", "A"));
    assert.notOk(sameStrChar("AAA", "a"));
    assert.ok(sameStrChar("A", "A"));
  });
});

// Tests of addIfNotPresent function
QUnit.module("addIfNotPresent", function(hooks) {
  QUnit.test("common usage", function(assert) {
    let arr = [];
    addIfNotPresent(arr, "a");
    assert.deepEqual(arr, ["a"]);
    addIfNotPresent(arr, "a");
    assert.deepEqual(arr, ["a"]);
    addIfNotPresent(arr, "b");
    assert.deepEqual(arr, ["a", "b"]);
  });
});

// Tests of safeArrayDelete function
QUnit.module("safeArrayDelete", function(hooks) {
  QUnit.test("common usage", function(assert) {
    let arr = [1, 2, 3];
    safeArrayDelete(arr, 3);
    assert.deepEqual(arr, [1, 2]);
    safeArrayDelete(arr, 4);
    assert.deepEqual(arr, [1, 2]);
  });
});

// Tests of clippingForPlateType function
QUnit.module("clippingForPlateType", function(hooks) {
  QUnit.test("common usage", function(assert) {
    assert.equal(clippingForPlateType("16S library prep"), 100);
    assert.equal(clippingForPlateType("shotgun library prep"), 30);
    assert.equal(clippingForPlateType("compressed gDNA plates"), 20);
    assert.equal(clippingForPlateType("gDNA"), 20);
    assert.equal(clippingForPlateType("not a valid type"), 10000);
  });
});

QUnit.module("getSubstringMatches", function(hooks) {
  QUnit.test("common usage", function(assert) {
    assert.deepEqual(getSubstringMatches("w", ["wahoo", "walrus"]), [
      "wahoo",
      "walrus"
    ]);
    assert.deepEqual(getSubstringMatches("h", ["wahoo", "walrus"]), ["wahoo"]);
    assert.equal(getSubstringMatches("z", ["wahoo", "walrus"]).length, 0);
    assert.deepEqual(getSubstringMatches("1234f", ["01234f", "01234"]), [
      "01234f"
    ]);
    assert.deepEqual(
      getSubstringMatches("abc", ["abc", "ABCDEF", "AbCdE", "", "DEF"]),
      ["abc", "ABCDEF", "AbCdE"]
    );
  });
  QUnit.test("empty query text and/or empty strings in array", function(
    assert
  ) {
    assert.equal(getSubstringMatches("", ["wahoo", "walrus"]).length, 0);
    assert.equal(getSubstringMatches("", ["wahoo", "walrus", ""]).length, 0);
    assert.equal(getSubstringMatches("abc", ["wahoo", "walrus", ""]).length, 0);
    assert.deepEqual(getSubstringMatches("w", ["wahoo", "walrus", ""]), [
      "wahoo",
      "walrus"
    ]);
  });
});
