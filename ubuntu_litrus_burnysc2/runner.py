#[
#    <AIBuild.RandomBuild: 1>, 
#    <AIBuild.Rush: 2>, 
#    <AIBuild.Timing: 3>, 
#    <AIBuild.Power: 4>, 
#    <AIBuild.Macro: 5>, 
#    <AIBuild.Air: 6>
#]
# 
#[
#    <Difficulty.VeryEasy: 1>, 
#    <Difficulty.Easy: 2>, 
#    <Difficulty.Medium: 3>, 
#    <Difficulty.MediumHard: 4>, 
#    <Difficulty.Hard: 5>, 
#    <Difficulty.Harder: 6>, 
#    <Difficulty.VeryHard: 7>, 
#    <Difficulty.CheatVision: 8>, 
#    <Difficulty.CheatMoney: 9>, 
#    <Difficulty.CheatInsane: 10>
#]

from mm import MM
from from_example_proxy_rax import ProxyRaxBot

import sc2
from sc2 import run_game, maps, Race#, Difficulty
from sc2.player import Bot, Computer

run_game(
    maps.get('Thunderbird LE'),
    [ Bot(Race.Terran, MM()), Bot(Race.Terran, ProxyRaxBot()) ],
    realtime=True
)
