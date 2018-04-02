# GeolocationCode


ere We are using twisted frame work so mabld.py will run like 
--------------------------------------------------------------
example:     twistd -ny mabld.py

While running if it is asking to download twisted, use the command given below:
---------------------------------------------------------------------------------
>sudo pip install twisted

At the end of the installation process, if it shows any compilation error, use the command:
--------------------------------------------------------------------------------------------
>sudo apt-get  update; sudo apt-get install  python-dev -y

After using this command, again download twisted

* if it is not happening even after doing pip install twisted, use the following command:
------------------------------------------------------------------------------------------
>sudo apt-get install python-twisted

While running if it shows failed to reload (myserver/lib) then you have to do export of python path.
---------------------------------------------------------------------------------------------------------------------
export PYTHONPATH=`pwd`:`pwd`/lib

For downloading the jsonrpc in python
--------------------------------------
wget https://pypi.python.org/packages/83/68/fb79f7a5154cb9fea93ae1a00b2d0aed3527c79b8a30649a902a3eaf7846/txJSON-RPC-0.5.tar.gz
sudo tar txJSON-RPC-0.5.tar.gz
cd txJSON-RPC-0.5/
sudo python setup.py install

For error=====>'module' object has no attribute 'OP_NO_TLSv1_1'
----------------------------------------------------------------
pip install --upgrade pyopenssl

For error=====>fatal error: openssl/opensslv.h: No such file or directory
-------------------------------------------------------------------------
sudo apt-get install python-pip python-dev libffi-dev libssl-dev libxml2-dev libxslt1-dev libjpeg8-dev zlib1g-dev

