import sc2

from sc2 import run_game, maps, Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from sc2.player import Bot, Computer

from typing import List, Dict

class Basic(sc2.BotAI):
    def __init__(self):
        self.distance_calculation_method: int = 2
        self.raw_affects_selection: bool = True
        self.unit_command_uses_self_do: bool = False # TODO: what does this do?

        # self.worker_tracking: Dict[Unit, UnitTypeId] = dict()

    async def progression_loop(self):
        # TODO: i can't deal with this shit... OK so,
        #       the call to self.structures(<cc>).first ALWAYS
        #       returns a new object.... WTF
        cc: Unit = self.structures(UnitTypeId.COMMANDCENTER).first
        
        # train SCVs until we hit roughly 19 workers, 16 min / 3 gas
        if (
            self.can_afford(UnitTypeId.SCV) 
            and cc.is_idle
            and self.supply_workers < (16 + 3)
            and self.supply_left >= 1
        ): 
            cc.train(UnitTypeId.SCV)

        def supply_left_threshold(self):
            return max(3, int(self.supply_used/10))
            
        def self.supply_depot_amount_threshold(self):
            return max(1, int(self.supply_used/20))

        # build depots as necessary
        # TODO: figure out a more precise way to build the depos 
        #       at specific locs / patterns...
        # TODO: figure out how to make more supply depots 
        #       as more supply happens...
        # TODO: figure out good 'distance' and 'placement_step' values...
        if (
            self.supply_left < self.supply_left_threshold()
            and self.already_pending(UnitTypeId.SUPPLYDEPOT) 
                < self.supply_depot_amount_threshold()
        ):
            target: Point2 = self.start_location.towards(
                self.game_info.map_center, 
                distance=5)
            await self.build(
                UnitTypeId.SUPPLYDEPOT, 
                near=target, 
                placement_step=1)
        
        # iterate thru all depots and make sure they are LOWERED
        for depo in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            depo(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        
        # build a refinery once we hit 16 workers
        if (
            self.workers.amount >= 16
            and self.can_afford(UnitTypeId.REFINERY)
            and (self.structures(UnitTypeId.REFINERY).amount 
                 + self.already_pending(UnitTypeId.REFINERY)) < 1
        ):
            cc: Unit = self.townhalls(UnitTypeId.COMMANDCENTER).first
            vg: Unit = self.vespene_geyser.closer_than(10, cc).first
            w: Unit = self.workers.random
            w.build(UnitTypeId.REFINERY, vg)
        
        # route idle workers back to minerals
        for scv in self.workers.idle:
            scv.smart(self.mineral_field.closest_to(cc))
            
        # TODO: check to ensure there are 3 - 16 distribution of 
        #       workers on gas - minerals that doesn't use
        #       the 'distribute_workers()' method
        await self.distribute_workers()
            
        # build up to 3 rax
        # NOTE: we can get away with not checking 
        #       self.already_pending(<barracks>) because
        #       we don't accumulate enough minerals 
        #       that quickly anyway...
        # NOTE2: self.already_pending is only for queued buildings, 
        #        self.buildings(<barracks>) will accumulate all constructed 
        #        AND currently-being-built buildings as well
        # TODO: figure out a way to only pull scvs that are mining minerals...
        if (
            self.can_afford(UnitTypeId.BARRACKS)
            and self.structures(UnitTypeId.BARRACKS).amount < 3
        ):
            map_center: Point2 = self.game_info.map_center
            target: Point2 = self.start_location.towards(
                map_center, 
                distance=5)
            await self.build(
                UnitTypeId.BARRACKS, 
                near=target, 
                placement_step=1)
            
        # set rally points of ready rax towards the ramp...
        for rax in self.structures(UnitTypeId.BARRACKS).ready:
            rax.smart(self.main_base_ramp.barracks_in_middle)
            
        # build marines forever! >:)
        for rax in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.can_afford(UnitTypeId.MARINE):
                rax.train(UnitTypeId.MARINE)

        # attack enemy base with waves of 15 units
        # NOTE: assume there is at least one enemy start location?
        # NOTE2: use of '.idle' is IMPORTANT! this allows us to 
        #        send marines in batches, since units simply sitting 
        #        around will be idle and ones attacking 
        #        the enemy base won't be selected...
        marines: Units = self.units(UnitTypeId.MARINE).idle
        if marines.amount > 15:
            target: Point2 = self.enemy_start_locations[0].position
            for marine in marines:
                marine.attack(target)
        
    async def on_start(self):
        # NOTE: sc2 updates 22.4 frames/sec on 'faster'
        self.client.game_step: int = 22 
        
    async def on_step(self, iteration: int):
        await self.progression_loop()

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

run_game(
    maps.get('Acropolis LE'),
    [ Bot(Race.Terran, Basic()), Computer(Race.Random, Difficulty.Medium) ],
    realtime=True
)

