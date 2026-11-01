# User guide text (for `pcbthermal/help/index.html`, import chapter), to adopt with the feature

## Which program made these files?

When you open a Gerber set, the import window reads the first lines of every file and tells you which program probably wrote them, for example **"Detected: Altium Designer 24.5.2 (declared in the files, high confidence)"**. The answer comes from what the files say about themselves: the standard Gerber attribute `TF.GenerationSoftware`, comment lines such as `G04 EAGLE Gerber RS-274X export`, the header of the drill file, and files that come with the set (a plot setup, an extension report). It is only a **starting point**: you can always choose another program in the list next to it (**change...**) or **Unknown program**, and your choice is kept with the project.

**What the program changes.** It decides how the files are named and read when they do not say it themselves: Xpedition's `EtchLayerTop.gdo` is the top copper, Allegro's `lyr2.art` an inner layer, Target 3001's `.Top` the top copper; where the board outline is; and which small quirks of the drill and Gerber files of that program are tolerated. A file that says what it is (the standard X2 attribute, an Excellon header) is never overruled by the program choice. The choice never changes a result by itself: it changes which files are taken as copper, drill and outline, which you see and confirm in the layer list.

**Confidence.** *High*: the files name the program. *Several programs*: files from more than one program are in the set, check the list. *Probably*: a typical quirk or file name, no banner. *Unknown program*: nothing matched; the files are read by their attributes and names (as before). If the files declare a program that is not in the list, its name is shown.

**Not recognised or not tested.** Zuken (CR-8000, CR-5000, CADSTAR), PADS Professional, Valor, Allegro X, OrCAD X, EasyEDA Pro and Horizon EDA could not be tested with real files; choose **Unknown program** and assign the layers by hand, and send us a small set of files (the first thirty lines of one Gerber file and one drill file are enough) so that the program can learn it. You can add a program yourself in the user defaults file (only the differences are stored).

**Two things the program does not preset**: the sign of the X coordinate of bottom-side parts in a placement file (some tools negate it when you ask for it; the program checks it against the solder paste) and the part names in the paste layer (they exist only if you asked the tool to write them).
