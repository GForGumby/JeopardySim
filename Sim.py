import streamlit as st
import random
from typing import Dict, List, Tuple
import numpy as np
from dataclasses import dataclass
from collections import defaultdict
import plotly.graph_objects as go

@dataclass
class GameState:
    """Represents the current state of a Jeopardy game."""
    player_money: float
    opponent1_money: float
    opponent2_money: float
    remaining_value: float  # Total $ value remaining on board
    dd_probability: float
    player_clue_probability: float
    fj_probability: float  # Probability of getting Final Jeopardy correct
    opp1_fj_probability: float  # Opponent 1's FJ success rate
    opp2_fj_probability: float  # Opponent 2's FJ success rate
    is_double_jeopardy: bool = True

class JeopardySimulator:
    def __init__(self, num_simulations: int = 500):
        self.num_simulations = num_simulations
        self.clue_values = list(range(200, 2001, 100))  # All possible clue values
        
    # [Previous methods remain the same - get_strategic_wagers, simulate_remaining_clues, 
    # simulate_final_jeopardy, simulate_game, and run_simulations stay identical]
    
    def get_strategic_wagers(self, money: float, position: str, leader_money: float, second_money: float) -> List[float]:
        """Generate strategic wager options based on position and money totals."""
        wagers = set()
        
        if position == "leader":
            wagers.add(0)  # Protect lead
            wagers.add(money)  # All in
            second_double = second_money * 2
            if second_double > money:
                wagers.add(money)
            else:
                wagers.add(second_double - money + 1)
            for pct in [0.25, 0.5, 0.75]:
                wagers.add(int(money * pct))
                
        elif position == "second":
            wagers.add(money)
            wagers.add(0)
            min_to_win = leader_money - money + 1
            if min_to_win <= money:
                wagers.add(min_to_win)
            for pct in [0.25, 0.5, 0.75]:
                wagers.add(int(money * pct))
                
        else:  # Third
            wagers.add(money)
            wagers.add(0)
            for pct in [0.25, 0.5, 0.75]:
                wagers.add(int(money * pct))
        
        return sorted(list(wagers))

    def simulate_remaining_clues(self, game_state: GameState, player_money: float,
                               opp1_money: float, opp2_money: float) -> Dict:
        """Simulate remaining regular clues."""
        player = player_money
        opp1 = opp1_money
        opp2 = opp2_money
        remaining = game_state.remaining_value
        
        opp_probability = (1 - game_state.player_clue_probability) / 2
        
        while remaining > 0:
            possible_values = [v for v in self.clue_values if v <= remaining]
            if not possible_values:
                break
                
            value = random.choice(possible_values)
            remaining -= value
            
            r = random.random()
            if r < game_state.player_clue_probability:
                player += value
            elif r < game_state.player_clue_probability + opp_probability:
                opp1 += value
            else:
                opp2 += value
        
        return {'player': player, 'opp1': opp1, 'opp2': opp2}

    def simulate_final_jeopardy(self, player: float, opp1: float, opp2: float, game_state: GameState) -> Dict:
        """Simulate Final Jeopardy round with strategic wagering."""
        money_positions = sorted([(player, "player"), (opp1, "opp1"), (opp2, "opp2")], 
                               key=lambda x: x[0], reverse=True)
        positions = {item[1]: pos for pos, item in enumerate(money_positions)}
        
        if positions["player"] == 0:
            player_wagers = self.get_strategic_wagers(player, "leader", player, money_positions[1][0])
        elif positions["player"] == 1:
            player_wagers = self.get_strategic_wagers(player, "second", money_positions[0][0], player)
        else:
            player_wagers = self.get_strategic_wagers(player, "third", money_positions[0][0], money_positions[1][0])
            
        best_win_rate = 0
        best_wager = 0
        total_sims = 100
        
        for player_wager in player_wagers:
            wins = 0
            
            for _ in range(total_sims):
                if positions["opp1"] == 0:
                    opp1_wager = random.choice(self.get_strategic_wagers(opp1, "leader", opp1, money_positions[1][0]))
                elif positions["opp1"] == 1:
                    opp1_wager = random.choice(self.get_strategic_wagers(opp1, "second", money_positions[0][0], opp1))
                else:
                    opp1_wager = random.choice(self.get_strategic_wagers(opp1, "third", money_positions[0][0], money_positions[1][0]))
                    
                if positions["opp2"] == 0:
                    opp2_wager = random.choice(self.get_strategic_wagers(opp2, "leader", opp2, money_positions[1][0]))
                elif positions["opp2"] == 1:
                    opp2_wager = random.choice(self.get_strategic_wagers(opp2, "second", money_positions[0][0], opp2))
                else:
                    opp2_wager = random.choice(self.get_strategic_wagers(opp2, "third", money_positions[0][0], money_positions[1][0]))
                
                player_final = player + (player_wager if random.random() < game_state.fj_probability else -player_wager)
                opp1_final = opp1 + (opp1_wager if random.random() < game_state.opp1_fj_probability else -opp1_wager)
                opp2_final = opp2 + (opp2_wager if random.random() < game_state.opp2_fj_probability else -opp2_wager)
                
                if player_final > max(opp1_final, opp2_final):
                    wins += 1
            
            win_rate = wins / total_sims
            if win_rate > best_win_rate:
                best_win_rate = win_rate
                best_wager = player_wager
        
        return {
            'optimal_fj_wager': best_wager,
            'fj_win_rate': best_win_rate
        }

    def simulate_game(self, game_state: GameState, dd_bet: float) -> Dict:
        """Simulate entire game including Daily Double and Final Jeopardy."""
        player = game_state.player_money
        opp1 = game_state.opponent1_money
        opp2 = game_state.opponent2_money
        
        if random.random() < game_state.dd_probability:
            player += dd_bet
        else:
            player -= dd_bet
            
        final_regular = self.simulate_remaining_clues(game_state, player, opp1, opp2)
        player = final_regular['player']
        opp1 = final_regular['opp1']
        opp2 = final_regular['opp2']
        
        fj_results = self.simulate_final_jeopardy(player, opp1, opp2, game_state)
        
        return {
            'pre_fj_player': player,
            'pre_fj_opp1': opp1,
            'pre_fj_opp2': opp2,
            'fj_results': fj_results
        }

    def run_simulations(self, game_state: GameState) -> Dict:
        """Run multiple simulations for different DD bet amounts."""
        max_bet = (2000 if game_state.is_double_jeopardy else 1000) if game_state.player_money < 1000 else game_state.player_money
        
        results = {}
        best_combined_rate = 0
        optimal_bet = 0
        
        for bet in range(0, int(max_bet) + 1000, 1000):
            if bet > max_bet:
                continue
                
            sim_results = []
            
            for _ in range(self.num_simulations):
                result = self.simulate_game(game_state, bet)
                sim_results.append(result)
            
            avg_fj_win_rate = np.mean([r['fj_results']['fj_win_rate'] for r in sim_results])
            
            results[bet] = {
                'pre_fj_results': sim_results,
                'avg_fj_win_rate': avg_fj_win_rate
            }
            
            if avg_fj_win_rate > best_combined_rate:
                best_combined_rate = avg_fj_win_rate
                optimal_bet = bet
        
        return {
            'optimal_bet': optimal_bet,
            'best_win_rate': best_combined_rate,
            'detailed_results': results
        }

def create_win_rate_chart(results: Dict):
    """Create a Plotly chart showing win rates for different bets."""
    bets = []
    win_rates = []
    
    for bet, stats in sorted(results['detailed_results'].items()):
        bets.append(bet)
        win_rates.append(stats['avg_fj_win_rate'] * 100)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=bets,
        y=win_rates,
        mode='lines+markers',
        name='Win Rate'
    ))
    
    fig.update_layout(
        title='Win Rates by Daily Double Bet',
        xaxis_title='Daily Double Bet ($)',
        yaxis_title='Win Rate (%)',
        hovermode='x'
    )
    
    return fig

def main():
    st.set_page_config(page_title="Jeopardy Strategy Simulator", layout="wide")
    
    st.title("Jeopardy Daily Double and Final Jeopardy Simulator")
    st.write("This simulator helps determine optimal betting strategy considering both Daily Double and Final Jeopardy rounds.")
    
    # Create two columns for input
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Current Game State")
        player_money = st.number_input("Your current money ($)", min_value=0, value=1000, step=100)
        opp1_money = st.number_input("Opponent 1's money ($)", min_value=0, value=800, step=100)
        opp2_money = st.number_input("Opponent 2's money ($)", min_value=0, value=600, step=100)
        remaining_value = st.number_input("Total $ value of remaining clues", min_value=0, value=2000, step=100)
        is_double = st.checkbox("Is this Double Jeopardy?", value=True)
    
    with col2:
        st.subheader("Success Probabilities")
        dd_prob = st.slider("Your Daily Double success probability (%)", 0, 100, 80) / 100
        clue_prob = st.slider("Your subsequent clue probability (%)", 0, 100, 33) / 100
        fj_prob = st.slider("Your Final Jeopardy success probability (%)", 0, 100, 60) / 100
        opp1_fj_prob = st.slider("Opponent 1's Final Jeopardy probability (%)", 0, 100, 60) / 100
        opp2_fj_prob = st.slider("Opponent 2's Final Jeopardy probability (%)", 0, 100, 60) / 100
    
    if st.button("Run Simulation"):
        with st.spinner("Running simulations..."):
            # Create game state
            state = GameState(
                player_money=player_money,
                opponent1_money=opp1_money,
                opponent2_money=opp2_money,
                remaining_value=remaining_value,
                dd_probability=dd_prob,
                player_clue_probability=clue_prob,
                fj_probability=fj_prob,
                opp1_fj_probability=opp1_fj_prob,
                opp2_fj_probability=opp2_fj_prob,
                is_double_jeopardy=is_double
            )
            
            # Run simulations
            simulator = JeopardySimulator(num_simulations=500)
            results = simulator.run_simulations(state)
            
            # Display results
            st.subheader("Simulation Results")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Optimal Daily Double Bet", f"${results['optimal_bet']:,}")
                st.metric("Expected Win Rate", f"{results['best_win_rate']:.1%}")
            
            # Display win rate chart
            st.subheader("Win Rates by Bet Amount")
            fig = create_win_rate_chart(results)
            st.plotly_chart(fig, use_container_width=True)
            
            # Detailed results table
            st.subheader("Detailed Results")
            data = []
            for bet, stats in sorted(results['detailed_results'].items()):
                data.append({
                    "Daily Double Bet": f"${bet:,}",
                    "Win Rate": f"{stats['avg_fj_win_rate']:.1%}"
                })
            st.table(data)

if __name__ == "__main__":
    main()
