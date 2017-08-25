# epub_images
Download of images to embed them for 'Almanacco dello spazio', www.almanaccodellospazio.it

This script simply read the html files presents in the epub and scans for image reference.

When it find an image the url is replaced with a local copy reference and the file is downloaded.

At the end all the directory is packed up in a .epub file that has all the images embedded.

To use the script you need the python interpreter, at least version 3.5, and the original .epub file.

The simplest way to use this is to clone the repository in a local directory, copy the epub file in the 
same directory and run the script. 

If you don't pass any option the standard file name is used (almanaccodellospazio.epub), if you
want to use a different name pass it on the command line, e.g.

```
python ads_cvt.py almanacco_test.epub

```

The resulting file is always called 'almanaccodellospazio-immagini.epub'

The script is been tested on windows 10 with the official python 3.5.2 version and on 
ubuntu gnome 16.04, where you need to call the script with python3:

```
python3 ads_cvt.py 

```






