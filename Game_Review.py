from scipy.optimize import root_scalar
from stockfish import Stockfish
from chessdotcom import get_player_game_archives, Client
from math import exp
import chess
import requests
import pprint

class GameReview:
    def __init__(self,username):
        self.username = username
        Client.request_config["headers"]["User-Agent"] = ("My Python Application. Contact me at email@example.com")
        self.PIECE_VALUES = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 1000
        }
        self.allgames = self.fetch_all_games()
        self.board = chess.Board()
        self.stockfish = Stockfish("/opt/render/project/src/stockfish")
        #self.stockfish = Stockfish("/usr/local/bin/stockfish")
        self.prev_eval = 0
        self.eval = 39
        self.opening = ""
        
    #v = eval
    def winning_chance(self,v):
        return round(1/(1+exp(-v/200)),2)

    def fetch_all_games(self):
        response = get_player_game_archives(self.username)
        data = response.json
        games = []

        for archive_url in data['archives']:
            headers = {"User-Agent": "My Python Application. Contact me at email@example.com"}
            archive_response = requests.get(archive_url, headers=headers)
            archive_response.raise_for_status()  # Raises HTTPError for bad responses (4xx and 5xx)
            games_data = archive_response.json()['games']
            games.extend([game for game in games_data if game.get('rules') == 'chess'  and '1.' in game['pgn']])
        return games

    def getEval(self,evaluation):
        if evaluation['type'] == 'mate':
            if evaluation['value'] > 0:
                return float('inf')
            elif evaluation['value'] < 0:
                return float('-inf')
            else:
                return self.prev_eval
        else:
            return evaluation['value']

    def read_move_eval(self,move):
        #pprint.pp(move)
        if move['Mate'] != None:
            if move['Mate'] > 0:
                return float('inf')
            elif move['Mate'] < 0:
                return float('-inf')
            else:
                return self.prev_eval
        else:
            return move['Centipawn']

    def evaluate_material(self,board):
        material_score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece:
                value = self.PIECE_VALUES[piece.piece_type]
                material_score += value if piece.color == chess.WHITE else -value
        return material_score

    def is_hanging(self,board, target_square):
        piece = board.piece_at(target_square)
        if not piece:
            return False
        
        color = piece.color
        attackers = list(board.attackers(not color, target_square))
        defenders = list(board.attackers(color, target_square))

        if len(attackers) == 0:
            return False
        #doesnt understand x-ray defense
        attackers.sort(key=lambda sq: self.PIECE_VALUES[board.piece_at(sq).piece_type])
        defenders.sort(key=lambda sq: self.PIECE_VALUES[board.piece_at(sq).piece_type])
        
        target_value = self.PIECE_VALUES[piece.piece_type]
        attacker_material_loss = 0
        defender_material_loss = 0
        attacked = False
        while attackers or defenders:
            if attackers:
                while True:
                    try:
                        attacker_square = attackers.pop(0)
                        attacker_piece_value = self.PIECE_VALUES[board.piece_at(attacker_square).piece_type]
                        move = board.parse_san(chess.square_name(attacker_square)+chess.square_name(target_square))
                        board.push(move)
                        #print(move)
                        break
                    except Exception:
                        if len(attackers) == 0:
                            if len(defenders) > 0 or not attacked:
                                return False
                            else:
                                return True
                        continue
                if len(defenders) > 0:
                    attacker_material_loss += attacker_piece_value
                
                if attacker_material_loss < target_value:
                    return True
                attacked = True
                target_value = attacker_piece_value
            
            if defenders:
                while True:
                    try:
                        defender_square = defenders.pop(0)
                        defender_piece_value = self.PIECE_VALUES[board.piece_at(defender_square).piece_type]
                        move = board.parse_san(chess.square_name(defender_square)+chess.square_name(target_square))
                        board.push(move)
                        break
                    except Exception:
                        if len(defenders) == 0:
                            if len(attackers) > 0:
                                return True
                            else:
                                return False
                        continue
                    
                if len(attackers) > 0:
                    defender_material_loss += defender_piece_value
                
                if defender_material_loss > target_value:
                    return True
                target_value = defender_piece_value
        
        return False

    def hanging_pieces(self,board,col):
        h = 0
        color = col
        if col:
            col = chess.WHITE
        else:
            col = chess.BLACK
        #pawn_only = True    
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece and piece.color == col and self.is_hanging(board.copy(),square):
                '''print()
                attackers = list(board.attackers(not color, square))
                defenders = list(board.attackers(color, square))
                print(chess.square_name(square))
                attackers = [chess.square_name(square) for square in attackers]
                defenders = [chess.square_name(square) for square in defenders]
                print('Attackers:',attackers)
                print('Defenders:',defenders)
                print()'''
                value = self.PIECE_VALUES[piece.piece_type]
                h += value
                '''if value > 1:
                    pawn_only = False'''
        if col == chess.BLACK:
            h *= -1
        return h

    def isBrilliantMove(self,board):
        b_move = board.pop()
        self.stockfish.set_fen_position(board.fen())
        white = board.turn == chess.WHITE
        if not ((white and self.eval >= -200) or (not white and self.eval <= 200)):
            #print('Died at First Level: ',b_move,';',white,eval)
            return False
        top4 = self.stockfish.get_top_moves(min(4,len(list(board.legal_moves))))
        move1 = self.winning_chance(self.read_move_eval(top4[0]))
        move4 = self.winning_chance(self.read_move_eval(top4[-1]))
        if ((self.eval >= 200 and white) or (self.eval <= -200 and not white)) and round(abs(move1-move4),2) < 0.08:
            #print('Died at Second Level: ',move1,move4,b_move)
            return False
        board.push(b_move)
        self.stockfish.set_fen_position(board.fen())
        h = self.hanging_pieces(board,white)
        #h > m white, h < m black
        if abs(h) < 2:
            #print('Died at Third Level: ',b_move,';',h,white)
            return False
        m = self.evaluate_material(board)
        
        best_move = self.stockfish.get_best_move()
        if best_move == None:
            return False
        #print('Possible Capture:',best_move)
        while board.piece_at(chess.parse_square(best_move[2:4])):
            self.stockfish.make_moves_from_current_position([best_move])
            board.push(board.parse_san(best_move))
            #print('Capture:',best_move)
            best_move = self.stockfish.get_best_move()
        #print(board.fen())

        em = self.evaluate_material(board)
        h = self.hanging_pieces(board,white)
        h += em-m
        if not(abs(h)>=2 and ((m-h <= 0 and white) or (m-h >= 0 and not white))):
            #print('Died at Fourth Level: ',b_move,';',m,em,h,white)
            return False
        return True
        
    def classify_move(self,diff):
        if diff <= 0.02:
            board2 = self.board.copy()
            if self.isBrilliantMove(board2):
                self.stockfish.set_fen_position(self.board.fen())
                return 'Brilliant'
            self.stockfish.set_fen_position(self.board.fen())
        if diff == 0:
            last_move = self.board.pop()
            self.stockfish.set_fen_position(self.board.fen())
            try:
                move1,move2 = self.stockfish.get_top_moves(2)
                move1 = self.winning_chance(self.read_move_eval(move1))
                move2 = self.winning_chance(self.read_move_eval(move2))
                self.board.push(last_move)
                self.stockfish.set_fen_position(self.board.fen())
            except:
                self.board.push(last_move)
                self.stockfish.set_fen_position(self.board.fen())
                return 'Best'
            if round(abs(move1-move2),2) >= 0.08:
                return 'Great'
            return 'Best'
        elif diff <= 0.02:
            return 'Excellent'
        elif diff <= 0.04:
            return 'Good'
        elif diff <= 0.08:
            return 'Inaccuracy'
        elif diff <= 0.15:
            return 'Mistake'
        else:
            return 'Blunder'

    def get_accuracy(self,centipawn_loss,move_num):
        if move_num == 0: return 0.0
        acl = centipawn_loss/(move_num/2)
        return round(100/(1+0.007*acl),1)

    def get_master_game_count(self,fen):
        url = "https://explorer.lichess.ovh/masters"
        params = {
            'fen': fen,
        }

        response = requests.get(url, params=params)

        if response.status_code == 200:
            data = response.json()

            if 'opening' in data:
                #pprint.pp(data)
                try:
                    self.opening = data.get('opening').get('name')
                except:
                    pass
                return data.get('white', 0) + data.get('black', 0) + data.get('draws', 0)
            else:
                #print("No opening data found.")
                return 0
        else:
            #print(f"Failed to fetch data. Status code: {response.status_code}")
            return 0

    #brilliant_games = ['https://www.chess.com/game/live/41547062879','https://www.chess.com/game/live/53202648839','https://www.chess.com/game/live/56063024459','https://www.chess.com/game/live/58840794151', 'https://www.chess.com/game/live/70607560287', 'https://www.chess.com/game/live/70681965957', 'https://www.chess.com/game/live/70683838793', 'https://www.chess.com/game/live/71540014503', 'https://www.chess.com/game/live/71709275089', 'https://www.chess.com/game/live/71733127235', 'https://www.chess.com/game/live/72675106795', 'https://www.chess.com/game/live/73023265917', 'https://www.chess.com/game/live/76216810855', 'https://www.chess.com/game/live/76814354317', 'https://www.chess.com/game/live/82529512975', 'https://www.chess.com/game/live/83459797859', 'https://www.chess.com/game/live/86638151493', 'https://www.chess.com/game/live/86658504367', 'https://www.chess.com/game/live/87457919483', 'https://www.chess.com/game/live/88484444549', 'https://www.chess.com/game/live/89510435143', 'https://www.chess.com/game/live/95562619813', 'https://www.chess.com/game/live/96266047267', 'https://www.chess.com/game/live/98418311429', 'https://www.chess.com/game/live/99005048069', 'https://www.chess.com/game/live/99105850377', 'https://www.chess.com/game/live/99814368917', 'https://www.chess.com/game/live/99979944409', 'https://www.chess.com/game/live/100317705783', 'https://www.chess.com/game/live/100752757325', 'https://www.chess.com/game/live/101005933921', 'https://www.chess.com/game/live/101529678935', 'https://www.chess.com/game/live/101536285477', 'https://www.chess.com/game/live/102819636609', 'https://www.chess.com/game/live/102885674197', 'https://www.chess.com/game/live/103185063307', 'https://www.chess.com/game/live/103348892823', 'https://www.chess.com/game/live/103351332399', 'https://www.chess.com/game/live/103401128193', 'https://www.chess.com/game/live/103425696277', 'https://www.chess.com/game/live/104024397413', 'https://www.chess.com/game/live/104298047727', 'https://www.chess.com/game/live/104357973169', 'https://www.chess.com/game/live/104446273369', 'https://www.chess.com/game/live/104452187933', 'https://www.chess.com/game/live/104545192661', 'https://www.chess.com/game/live/104777541093', 'https://www.chess.com/game/live/104899878881', 'https://www.chess.com/game/live/105162668097', 'https://www.chess.com/game/live/105164407265', 'https://www.chess.com/game/live/105164422155', 'https://www.chess.com/game/live/105256181015', 'https://www.chess.com/game/live/106254996795', 'https://www.chess.com/game/live/106450595861', 'https://www.chess.com/game/live/106451260547', 'https://www.chess.com/game/live/107050292171', 'https://www.chess.com/game/live/107050820801', 'https://www.chess.com/game/live/107050869381'] #CHANGE TO EMPTY LATER

    def gameReview(self,url_input):
        url_input = url_input.split('/')[-1]
        url = ''
        i = 0
        while i < len(url_input) and url_input[i].isdigit():
            url += url_input[i]
            i+=1
        #print(url)

        index = 0
        while index < len(self.allgames) and self.allgames[index]['url'].split('/')[-1] != url:
            index+=1
        if index == len(self.allgames):
            pprint.pp("Game Not Found:",url_input)
            return
        game = self.allgames[index]['pgn']
        #pprint.pp(self.allgames[i])
        book = True
        self.opening = ""
        self.stockfish.set_fen_position("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
        moves = game.split()
        while moves[0] != '1.':
            moves.pop(0)
        i = 0
        while i < len(moves):
            if '.' in moves[i] or '{' in moves[i] or '}' in moves[i] or '0' in moves[i]:
                moves.pop(i)
            else:
                i += 1
        centipawns_lost_white = 0
        centipawns_lost_black = 0
        move_num = len(moves)
        review = []
        positions = []
        evals = []
        #move_ind = 1
        white = True
        for move in moves:
            try:
                self.prev_eval = self.read_move_eval(self.stockfish.get_top_moves(1)[0])
            except:
                break
            try:
                uci_move = self.board.parse_san(move)
                self.board.push(uci_move)
                self.stockfish.make_moves_from_current_position([uci_move.uci()])
            except:
                continue
            self.eval = self.getEval(self.stockfish.get_evaluation())
            positions.append(self.board.fen())
            if (self.eval == float('inf')):
                    evals.append("∞")
            elif (self.eval == float('-inf')):
                evals.append("-∞")
            else:
                evals.append(self.eval)
            #prev_eval, eval = eval, evaluation
            #print(prev_eval,eval,winning_chance(prev_eval),winning_chance(eval),move)
            if self.eval != float('inf') and self.eval != float('-inf') and self.prev_eval != float('inf') and self.prev_eval != float('-inf'):
                if white:
                    centipawns_lost_white += abs(self.prev_eval-self.eval)
                else:
                    centipawns_lost_black += abs(self.prev_eval-self.eval)
            else:
                move_num -= 1
            if book and self.get_master_game_count(self.board.fen()) >= 25:
                type = "Book"
            else:
                book = False
                type = self.classify_move(round(abs(self.winning_chance(self.eval)-self.winning_chance(self.prev_eval)),2))
            review.append(type)
            white = not white
        results = [review,moves,self.opening]
        user = [self.username]
        opp = []
        if self.username.lower() == self.allgames[index]['white']['username'].lower():
            user.append(self.allgames[index]['white']['rating'])
            opp.append(self.allgames[index]['black']['username'])
            opp.append(self.allgames[index]['black']['rating'])
            results.extend([user,opp])
        else:
            user.append(self.allgames[index]['black']['rating'])
            opp.append(self.allgames[index]['white']['username'])
            opp.append(self.allgames[index]['white']['rating'])
            results.extend([opp,user])

        results.append(str(self.get_accuracy(centipawns_lost_white,move_num))+'%')
        results.append(str(self.get_accuracy(centipawns_lost_black,move_num))+'%')
        results.append(positions)
        results.append(evals)
        return results