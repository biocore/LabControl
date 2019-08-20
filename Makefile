# NOTE 1: these targets require the "prettier" Node.js package is globally
# installed
#
# NOTE 2: this code was derived from Qurro's Makefile
# (https://github.com/biocore/qurro/blob/master/Makefile)
#
# NOTE 3: HTML code is currently not included in these operations, since it
# seems to break prettier. (I think some of that is due to actual HTML errors,
# but some of that seems to be due to the Tornado template syntax messing
# things up.)
.PHONY: festyle festylecheck

JS_CSS_CODE_LOCS = labcontrol/gui/static/js/*.js labcontrol/gui/static/css/labcontrol.css labcontrol/gui/js_tests/*.js
HTML_CODE_LOCS = labcontrol/gui/templates/*.html labcontrol/gui/js_tests/*.html

# This target auto-formats all of the JS and CSS code to be compliant with
# prettier.
festyle:
	@# To be extra safe, do a dry run of prettier and check that it hasn't
	@# changed the code's abstract syntax tree.
	prettier --debug-check $(JS_CSS_CODE_LOCS)
	prettier --write $(JS_CSS_CODE_LOCS)

# This target checks to make sure all of the JS and CSS code *is* compliant
# with prettier. Will be run on Travis.
festylecheck:
	prettier --check $(JS_CSS_CODE_LOCS)
