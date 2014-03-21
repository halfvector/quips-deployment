var gulp = require('gulp'),
    gutil = require('gulp-util');

var http = require('http'),
    runSequence = require('run-sequence'),
    sass = require('gulp-ruby-sass'),
//    autoprefixer = require('gulp-autoprefixer'),
//    minifycss = require('gulp-minify-css'),
    jshint = require('gulp-jshint'),
    rename = require('gulp-rename'),
    uglify = require('gulp-uglify'),
    clean = require('gulp-clean'),
    concat = require('gulp-concat'),
//    imagemin = require('gulp-imagemin'),
    cache = require('gulp-cache'),
//    open = require('gulp-open'),
    livereload = require('gulp-livereload'),
//    embedlr = require('gulp-embedlr'),
//    ecstatic = require('ecstatic'),
    lr = require('tiny-lr'),
    server = lr()
    ;

var jsDir = 'system/app/javascripts/';

var continueOnError = function(stream) {
    return stream
    .on('error', function(){})
    .on('pipe', function(src) {
        cleaner(src);
    })
    .on('newListener', function() {
        cleaner(this);
    });
};

var config = {
    livereload_port: "35729",

    src_html: "system/app/templates/*.html",

    src_sass: "system/app/stylesheets/*.sass",
    dest_css: "system/public/assets/css",

    // ready-libraries
    external_src_js: jsDir + 'libs/*.js',
    workers_src_js: jsDir + 'workers/*.js',

    // individual scripts
    main_src_js: [
        jsDir + 'app.js',
        jsDir + 'audio-capture.js',
        jsDir + 'homepage.js',
        jsDir + 'recording-control.js',
        jsDir + 'quip-control.js',
        jsDir + 'nav-user-dropdown.js'
    ],
    dest_js: "system/public/assets/js/",
    js_concat_main:  "main.js",
    js_concat_externals: "externals.js"
};

// sass task
gulp.task('styles', function () {
    return gulp.src(config.src_sass)
        .pipe(sass({style: "compact", sourcemap: false, cacheLocation: "tmp/sass-cache"}))
        .on('error', gutil.log)
        .pipe(gulp.dest(config.dest_css))
        .pipe(livereload(server))
});

// js: external libs
gulp.task('external-scripts', function () {
    return gulp.src(config.external_src_js)
        .pipe(rename(function(path) {
            if(path.basename.indexOf('.min') == -1)
                path.basename += '.min'
        }))
        .pipe(uglify())
        .pipe(concat(config.js_concat_externals))
        .pipe(gulp.dest(config.dest_js))
        .pipe(livereload(server))
});

// js: individual worker scripts
gulp.task('worker-scripts', function () {
    return gulp.src(config.workers_src_js)
        .pipe(rename(function(path) {
            if(path.basename.indexOf('.min') == -1)
                path.basename += '.min'
        }))
        .pipe(uglify())
        .pipe(gulp.dest(config.dest_js))
        .pipe(livereload(server))
});

// js: primary scripts
gulp.task('main-scripts', function () {
    return gulp.src(config.main_src_js)
        //.pipe(jshint(/* ".jshintrc" */))
        //.pipe(jshint.reporter('jshint-stylish'))
        .pipe(concat(config.js_concat_main))
        .pipe(gulp.dest(config.dest_js))
        .pipe(livereload(server))
});

// watch html
gulp.task('html', function () {
    return gulp.src(config.src_html)
        .pipe(livereload(server))
});

gulp.task('clean', function() {
  return gulp.src(['system/public/assets/css', 'system/public/assets/js'], {read: false})
    .pipe(clean());
});

// default task -- run 'gulp' from cli
gulp.task('default', function (callback) {
    runSequence('clean', ['external-scripts', 'worker-scripts', 'main-scripts', 'styles'], callback);
    server.listen(config.livereload_port);
    gulp.watch(config.src_sass, ['styles'])._watcher.on('all', livereload);
    gulp.watch(config.src_js, ['scripts'])._watcher.on('all', livereload);
    gulp.watch(config.external_src_js, ['external-scripts'])._watcher.on('all', livereload);
    gulp.watch(config.workers_src_js, ['worker-scripts'])._watcher.on('all', livereload);
    gulp.watch(config.main_src_js, ['main-scripts'])._watcher.on('all', livereload);
    gulp.watch(config.src_html, ['html'])._watcher.on('all', livereload);
});