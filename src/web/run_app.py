from flask import Flask, render_template, request, redirect
import pandas as pd
import numpy as np
import sys
import os
app = Flask(__name__)
app.gui_cols = ['artist_name','track_name','tempo','uri']
app.training_set = pd.DataFrame()
app.suggest_set = pd.DataFrame()
app.seed_uris = []
app.new_playlist = True


PROJ_ROOT = os.path.join(os.getcwd(), os.pardir, os.pardir)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)
pd.options.display.float_format = '{:,.3f}'.format

# load environment variables from .env file using dotenv.
from dotenv import load_dotenv
dotenv_path = os.path.join(PROJ_ROOT, '.env')
load_dotenv(dotenv_path)

# add the 'src' directory as one where we can import modules
src_dir = os.path.join(PROJ_ROOT, 'src')
sys.path.append(src_dir)

from data.spotipy_functions import *
from models.train_model import *

@app.route("/", methods=['GET'])
def home_page_get():
  return render_template("index.html")

@app.route("/display", methods=['GET','POST'])
def home_page_post():
  if request.method == 'POST':
    app.seed_uris = []
    for i in range(5):
      if request.form['uri{}'.format(i)] != '':
        app.seed_uris.append(request.form['uri{}'.format(i)][-22:])
    app.suggest_set = band_BPMs(get_new_recs_and_feats(app.seed_uris,30),80,170)
    if app.new_playlist:
      app.training_set = define_training_set(app.seed_uris)
      app.new_playlist = False
    else:
      if app.training_set.status.min() < 0:
        app.suggest_set = train_NB_model(app.suggest_set, app.training_set)    
  display_suggest_set = app.suggest_set[app.gui_cols + ['P_accept']]
  display_suggest_set.loc[:,'Accept'] = list(map(lambda x: '<a href="/accept/{0}">Accept</a>'.format(x), np.array(display_suggest_set.index)))
  display_suggest_set.loc[:,'Reject'] = list(map(lambda x: '<a href="/reject/{0}">Reject</a>'.format(x), np.array(display_suggest_set.index)))  
  display_suggest_set = display_suggest_set.sort_values(by=['P_accept'], ascending=False)
  display_training_set = app.training_set[app.training_set.status == 1][app.gui_cols]
  return render_template("output.html", seeds=app.seed_uris, training=display_training_set.to_html(escape=False), suggest=display_suggest_set.to_html(escape=False))

@app.route("/seed")
def seed_input():
  return render_template("seed_input.html")

@app.route("/accept/<suggest_id>")
def accept_track(suggest_id):
  suggest_id_int = int(suggest_id)
  app.suggest_set, app.training_set = process_track(app.suggest_set, app.training_set, suggest_id_int, 1)
  # only train the model when it has positive and negative examples
  if app.training_set.status.min() < 0:
    app.suggest_set = train_NB_model(app.suggest_set, app.training_set)
  return redirect('/display')

@app.route("/reject/<suggest_id>")
def reject_track(suggest_id):
  suggest_id_int = int(suggest_id)
  app.suggest_set, app.training_set = process_track(app.suggest_set, app.training_set, suggest_id_int, -1)
  app.suggest_set = train_NB_model(app.suggest_set, app.training_set)
  return redirect('/display')

if __name__ == "__main__":
  app.run(debug=True)