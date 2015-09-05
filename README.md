# quips-deployment
Deployment scaffolding for quips

Made for GNU/Linux
Porting it to also work on OSX

setup local env  
`fab dev prep` may work to some extent

clone quips-python into quips-deployment/system
then basic setup:
```
cp conf/app.ini system/conf/
cp conf/flask.ini system/conf/
mkdir -p system/public/recordings
mkdir -p system/public/profile_images
```
