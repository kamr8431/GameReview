from flask import Flask, request, render_template
from Game_Review import GameReview
import os

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/review',methods = ['POST'])
def review():
    ''' try:
        review = GameReview(username)
        results = review.gameReview(link)
    except Exception:
        return render_template('error.html')'''

# Use the current working directory as the starting point
    print(os.getcwd())
# Use the current working directory as the starting point
    for root, dirs, files in os.walk(os.getcwd()):
        for file in files:
            full_path = os.path.join(root, file)  # Combine the root directory with the file name
            print(full_path)
    username = request.form.get('username')
    link = request.form.get('game_link')
    return render_template('review.html', results = results, positions = positions, evals = evals)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)