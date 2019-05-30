import click
from os.path import join, abspath, dirname
from subprocess import Popen, PIPE
import os


'''
Notes: It's generally not a good idea to have Click commands call other click
commands, although ti can be done using context objects.

This means that it's better to have an umbrella command where users can specify
to turn off one or more tests, rather than have individual tests as separate
commands, with an umbrella command to call them all.
'''


# used to establish the 'cli' group of commands.
# all commands are specified on the command line as the first parameter.
@click.group()
def cli():
    pass


def run_js_test(timeout_in_milliseconds, html_file):
    '''helper function accepts a Qunit html file referencing javascript tests,
    executes it, and returns the results of the test.

    Returns
    -------
    tuple (bool, str):  True if no errors occured, False otherwise.
                        stdout from running tests.
    '''

    # params to node-qunit-puppeteer need to be encapsulated into one set of
    # quotes
    params = []
    params.append('--allow-file-access-from-files')
    params.append('--no-sandbox')
    params = ' '.join(params)

    cmd = []
    cmd.append('node-qunit-puppeteer')
    cmd.append(html_file)
    cmd.append(str(timeout_in_milliseconds))

    cmd.append('"%s"' % params)
    cmd = ' '.join(cmd)

    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE)
    o, e = p.communicate()
    o = o.decode("utf-8")
    e = e.decode("utf-8")

    # returncodes appear to be limited to 0 (success) and 1 (error).
    # all information appears to write out stdout; stderr is empty
    # on success or error.
    if p.returncode == 0:
        return(True, o)
    else:
        return(False, o)


# Currently, there is only one command. Add more commands here.
# note, the default has been explicitly defined here as 30,000ms. If none is
# supplied, the node_qunit_puppeteer script itself will default to 30,000ms.
@cli.command()
@click.option('--timeout_in_milliseconds', required=False,
              type=click.IntRange(0, None),
              default=30000, show_default=True,
              help='timeout for a unittest, in milliseconds')
def all_tests(timeout_in_milliseconds):
    '''Command to run all tests managed by this script. Currently there is only
    one (javascript qunit tests).

    Returns
    None:   System will exit with 0 if all tests were successful, 1 otherwise.
    '''

    click.echo('Run all tests')

    # assume all javascript qunit-based tests are referenced in one or more
    # html files that are located within the same directory as this file
    test_dir = abspath(dirname(__file__))

    # if a single test fails, this value will become False
    all_tests_successful = True

    # build a list of html files to process. The contents of this list will
    # then be processed in turn. The reason for this is to discover the number
    # of files to be processed, and set up the progress bar.
    html_files = []

    for path, sub_directories, files in os.walk(test_dir, topdown=False):
        for file in files:
            if file.endswith('.html'):
                html_files.append(join(path, file))

    click.echo("%d html files found" % len(html_files))

    count = len(html_files)

    # similarly, store the stdout of each test in results, instead of
    # displaying them as they are returned to us. This allows the progress bar
    # to properly stay in a single location and reach 100% when all tests have
    # completed.
    results = []

    with click.progressbar(length=count) as bar:
        for html_file in html_files:
            status, stdout = run_js_test(timeout_in_milliseconds, html_file)
            bar.update(1)
            results.append(stdout)
            if not status:
                all_tests_successful = False

    for result in results:
        click.echo(result)

    # returning 0 or 1 doesn't appear to percolate up as the return code for
    # this running script. Instead force an exit here with either 0 or 1,
    # depending on whether one or more tests errored out. (This is also like
    # Emperor.)
    if all_tests_successful:
        exit(0)

    exit(1)


if __name__ == '__main__':
    cli()
