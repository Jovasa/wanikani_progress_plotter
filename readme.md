A simple tool for plotting the number of items for each SRS stage.

The Wanikani API token needs to be stored in a file named `wanikani_token` without anything else, including trailing newline.

`data_collector` should be run each time a new data point should be generated. For example daily using a cronjob.
Currently, does not take advantage of ETags so do not run it unnecessarily.  