from contextlib import contextmanager
from fabric.api import *
from fabric.contrib.files import exists
import os

# no passwords here, host authentication is in  ~/.ssh/config
env.roledefs = {
    'development': ['localhost'],
    'production': ['git@what.you.say.icanhaserror.com:7693']
}
env.roles = ['development'] # default role is local dev

# TODO: try to crate an atomic deploy that knows how to roll-back
@contextmanager
def rollback_on_fail(rollback_callback):
    try:
        yield
    except SystemExit:
        rollback_callback()
        abort("Fail")

#
# local develoment tasks
#
@roles('development')
def dev():
    puts("local development mode")
    # all local paths are relative to this fabric file
    env.path = os.path.dirname(os.path.realpath(__file__))
    env.path_recordings = '%s/storage/recordings' % env.path
    env.path_profile_images = '%s/storage/profile_images' % env.path
    env.path_current = '%s/system' % env.path
    env.pip_build_cache = '%s/cache/pip.cache/' % env.path
    env.pip_download_cache = '%s/cache/pip.downloads/' % env.path
    puts("path: %s" % env.path)

@roles('development')
def prep():
    require('pip_download_cache', provided_by=[dev])
    puts("Bootstrapping python environment for local dev..")
    with lcd("system"):
        local('virtualenv --no-site-packages venv')
        with prefix('. venv/bin/activate'):
            # cache and re-use cache when possible
            local('pip install -q --download-cache %s -f %s pip-accel' % (env.pip_download_cache, env.pip_download_cache))
            local('PIP_DOWNLOAD_CACHE=%s PIP_ACCEL_CACHE=%s pip-accel install -q -r ../requirements.txt' % (
                env.pip_download_cache, env.pip_build_cache)
            )

@roles('development')
def dev_server():
    with lcd(os.path.dirname(os.path.realpath(__file__))):
        with lcd('system'), show('debug'), prefix('. venv/bin/activate'):
            local('uwsgi --ini ../conf/uwsgi.ini')

@roles('development')
def dev_server_debug():
    # start from a point relative to this file
    with lcd(os.path.dirname(os.path.realpath(__file__))):
        with lcd('system'), show('debug'), prefix('. venv/bin/activate'):
            local('python app/main.py webapp')

@roles('development')
def reload():
    with lcd(os.path.dirname(os.path.realpath(__file__))):
        local('touch tmp/uwsgi.sock')

def production():
    print "production server deployment mode"
    env.path = "/var/www/audio.icanhaserror.com"
    env.path_recordings = '%s/storage/recordings' % env.path
    env.path_profile_images = '%s/storage/profile_images' % env.path
    env.path_current = '%s/system' % env.path
    env.path_revisions = '%s/revisions' % env.path
    env.path_failsafe_revision = '%s/revisions/0-fallback' % env.path
    env.repo = '%s/repo.git' % env.path
    env.reload_file = '%s/tmp/uwsgi.sock' % env.path
    env.pip_build_cache = '%s/cache/pip.cache/' % env.path
    env.pip_download_cache = '%s/cache/pip.downloads/' % env.path
    puts("path: %s" % env.path)

def remote_uname():
    with cd(env.path):
        run('uname -a')

# preloads common files for deployment
def preload():
    print "stub: preloading common requirements"

def deploy_rollback():
    print "stub: rolling back deployment"

@roles('production')
def push_recordings():
    require('path_recordings', provided_by=[production])

    path = os.path.dirname(os.path.realpath(__file__))
    with lcd(path):
        put('recordings/*.ogg', env.path_recordings, mode=0664)

@roles('production')
def push_assets():
    require('path_current', provided_by=[production])

    path = os.path.dirname(os.path.realpath(__file__))
    with lcd(path):
        put('system/public/assets/img/*', '%s/public/assets/img/' % env.path_current, mode=0664)


# this is the good stuff right here
# 'git rev-parse production/master' will give you back the latest commit_id that made it over to the server
@roles('production')
def deploy(commit_id):
    require('path_revisions', provided_by=[production])

    path = os.path.dirname(os.path.realpath(__file__))
    with lcd(path):

        # verify commit_id hash is in git's log
        with hide('output','running','warnings'), settings(warn_only=True), lcd('system'):
            commit_test = local("git log %s -n 1 --oneline" % commit_id, True)
            if commit_test.startswith('fatal') or not commit_test.startswith(commit_id[:5]):
                print "Canceling deploy; log does not contain commit: %s" % commit_id
                return

        env.req_commit = commit_id
        env.req_path = '%(path_revisions)s/%(req_commit)s' % env

        # only proceed if deployed target hasn't been setup yet
        if exists(env.req_path):
            print "Canceling deploy; destination already exists, remove it to proceed"

        try:
            puts("Deploying commit: %s to %s" % (commit_id, env.req_path))
            with cd(env.path_revisions), hide('stdout'):
                run('git clone %(repo)s %(path_revisions)s/%(req_commit)s' % env, True)

            puts("Installing requirements..")
            with cd('%(path_revisions)s/%(req_commit)s' % env):
                run('virtualenv venv')
                with prefix('source venv/bin/activate'):
                    #run('easy_install -q -f %s pip-accel' % env.pip_download_cache)
                    # cache and re-use cache when possible
                    run('pip install -q --download-cache %s -f %s pip-accel' % (env.pip_download_cache, env.pip_download_cache))
                    run('PIP_DOWNLOAD_CACHE=%s PIP_ACCEL_CACHE=%s pip-accel install -q -r %s/requirements.txt' % (env.pip_download_cache, env.pip_build_cache, env.path))

            # setup static paths
            puts("Updating paths..")
            with cd(env.path):
                # public storage links
                run('ln -sfn %s %s/public/recordings' % (env.path_recordings, env.req_path))
                run('ln -sfn %s %s/public/profile_images' % (env.path_profile_images, env.req_path))

                # final step: link to new revision
                run('ln -sfn revisions/%s system' % commit_id)

            run('chown :quips %s' % env.req_path)

            # reload
            run('touch %s' % env.reload_file)

        except SystemExit:
            puts("Deploy failed; Removing bad-commit")
            remove(commit_id)


@roles('production')
def remove(commit_id):
    print "removing commit: %s" % commit_id
    env.req_commit = commit_id
    env.req_path = '%(path_revisions)s/%(req_commit)s' % env
    with cd(env.path_revisions):
        # rm -rf %s scares me, but mv %s scares me too
        # need a safe jailed way to do this
        # TODO: add path verification and user confirmation
        run('mv %s tmp_delete_me' % commit_id)
        run('rm -rf tmp_delete_me')

    # restore symlink if its broken
    with hide('commands'):
        if 'broken' in run('file %s' % env.path_current).stdout:
            print "Detected broken release symlink. falling back to failsafe."
            run('ln -sfnr %s %s' % (env.path_failsafe_revision, env.path_current))

    # reload
    run('touch %s' % env.reload_file)