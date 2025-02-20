from flask import Flask, request, render_template
from Game_Review import GameReview
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/review',methods = ['POST'])
def review():
    username = request.form.get('username')
    link = request.form.get('game_link')
    ''' try:
        review = GameReview(username)
        results = review.gameReview(link)
    except Exception:
        return render_template('error.html')'''
    review = GameReview(username)
    results = review.gameReview(link)
    evals = results.pop()
    positions = results.pop()
    return render_template('review.html', results = results, positions = positions, evals = evals)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)