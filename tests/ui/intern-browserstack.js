// Learn more about configuring this file at <https://github.com/theintern/intern/wiki/Configuring-Intern>.
// These default settings work OK for most people. The options that *must* be changed below are the
// packages, suites, excludeInstrumentation, and (if you want functional tests) functionalSuites.
define(['./_base', './_cli', 'intern'], function(config, cli, intern) {

    // Browsers to run integration testing against.
    config.environments = [
        { browserName: 'firefox', version: ['40'], platform: [ 'MAC' ] },
        { browserName: 'chrome', version: ['44'], platform: [ 'MAC' ] },
    ];

    // Name of the tunnel class to use for WebDriver tests
    config.tunnel = 'BrowserStackTunnel';

    // Format for outputting test results
    config.reporters = ['Pretty'];

    return cli.mixinArgs(intern.args, config);
});
