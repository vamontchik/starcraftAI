import sc2

from sc2 import run_game, maps, Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.position import Point2#, Point3
from sc2.unit import Unit
from sc2.unit_command import UnitCommand
from sc2.units import Units
from sc2.player import Bot, Computer

from typing import List, Dict

# TODO: if we wanna keep track of specific units or buildings, we can use their 'tag' fields...
# TODO: figure out a better way of placing down structures on the map...

class Basic(sc2.BotAI):
    def __init__(self):
        # TODO: (minor) should be most efficient dist calc?
        self.distance_calculation_method: int = 2 
        
        # TODO: is this necessary since this is the default...?
        self.unit_command_uses_self_do: bool = False

    async def progression_loop(self):    
        # NOTE: the call to self.structures(<cc>).first 
        #       ALWAYS returns a new object.... ???
        cc: Unit = self.structures(UnitTypeId.COMMANDCENTER).first
        
        # train SCVs until we hit roughly 22 workers, 16 min / 2x3 gas
        if (
            self.can_afford(UnitTypeId.SCV) 
            and cc.is_idle
            and self.supply_workers < (16 + 6)
            and self.supply_left >= 1
        ): 
            cc.train(UnitTypeId.SCV)
            
        # ensure 3 w / 16 on gas / minerals, respectively
        await self.distribute_workers()

        def supply_left_threshold():
            return max(3, int(self.supply_used/10))
            
        def supply_depot_amount_threshold():
            return max(1, int(self.supply_used/20))

        # build depots as necessary
        if (
            self.supply_left < supply_left_threshold()
            and self.already_pending(UnitTypeId.SUPPLYDEPOT) 
                < supply_depot_amount_threshold()
        ):
            target: Point2 = self.start_location.towards(
                self.game_info.map_center, 
                distance=4)
            await self.build(
                UnitTypeId.SUPPLYDEPOT, 
                near=target, 
                placement_step=1)
        
        # iterate thru all depots and make sure they are lowered
        for depo in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            depo(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        
        # build 2 refineries once we hit 16 workers
        if (
            self.workers.amount >= 16
            and self.can_afford(UnitTypeId.REFINERY)
            and self.structures(UnitTypeId.REFINERY).amount < 2
        ):
            vgs: Units = self.vespene_geyser.sorted_by_distance_to(cc)
            
            if self.built_first_ref == True:
                vg: Unit = vgs[1]
            else:
                vg: Unit = vgs[0]
                self.built_first_ref = True
            
            # NOTE: 'near' is really the exact target...
            await self.build(UnitTypeId.REFINERY, near=vg)
            
        # build 3 rax
        # NOTE: self.already_pending(<rax>) is for queued buildings
        #       AND current-being-built buildings,
        #       self.buildings(<rax>) will accumulate all constructed 
        #       AND currently-being-built buildings
        # NOTE2: above NOTE is why we ONLY use self.structures(<rax>)...
        # TODO: (minor) figure out a way to only pull scvs that are mining minerals...
        # TODO: figure out a BETTER way to place rax so there is always
        #       room for techlab / reactor upgrades...
        
        amt_rax: int = self.structures(UnitTypeId.BARRACKS).amount
        if (
            self.can_afford(UnitTypeId.BARRACKS)
            and amt_rax < 3
        ):
            if amt_rax == 0:        
                map_center: Point2 = self.game_info.map_center
                target: Point2 = self.start_location.towards(
                    map_center, 
                    distance=16)
                
                await self.build(
                    UnitTypeId.BARRACKS,
                    near=target,
                    placement_step=1)
            
            elif amt_rax == 1:
                target: Point2 = \
                    self.structures(UnitTypeId.BARRACKS)[0].position \
                    + Point2((0,3))
                
                await self.build(
                    UnitTypeId.BARRACKS,
                    near=target,
                    placement_step=1)
            
            elif amt_rax == 2:
                # find lower rax and then use it's position in calc
                both: Units = self.structures(UnitTypeId.BARRACKS)
                first: Unit = both[0]
                second: Unit = both[1]
                if first.position.y > second.position.y:
                    target: Unit = second.position + Point2((0,-3))
                else:
                    target: Unit = first.position + Point2((0,-3))
 
                await self.build(
                    UnitTypeId.BARRACKS,
                    near=target,
                    placement_step=1)
            
        # set rally points of ready rax towards the ramp...
        for rax in self.structures(UnitTypeId.BARRACKS).ready:
            rax.smart(self.main_base_ramp.barracks_in_middle)

        # build 2 tech labs and 1 reactor on rax
        if (
            self.rax_reactor < 1
            and self.can_afford(UnitTypeId.BARRACKSREACTOR)
        ):
            potential_rax: Units = self.structures(UnitTypeId.BARRACKS).filter(lambda rax: not rax.has_add_on).ready.idle
            if potential_rax.amount > 0:
                rax: Unit = potential_rax.random
                rax.build(UnitTypeId.BARRACKSREACTOR)
                self.rax_reactor += 1
        
        if (
            self.rax_techlab < 2
            and self.can_afford(UnitTypeId.BARRACKSTECHLAB)
        ):
            potential_rax: Units = self.structures(UnitTypeId.BARRACKS).filter(lambda rax: not rax.has_add_on).ready.idle
            if potential_rax.amount > 0:
                rax: Unit = potential_rax.random
                rax.build(UnitTypeId.BARRACKSTECHLAB)
                self.rax_techlab += 1
                
        # build an engineering bay AFTER we build 3 rax
        if (
            self.can_afford(UnitTypeId.ENGINEERINGBAY)
            and self.structures(UnitTypeId.BARRACKS).ready.amount == 3
            and self.structures(UnitTypeId.ENGINEERINGBAY).amount == 0
        ):
            map_center: Point2 = self.game_info.map_center
            target: Point2 = self.start_location.towards(
                map_center, 
                distance=4)
            await self.build(
                UnitTypeId.ENGINEERINGBAY, 
                near=target, 
                placement_step=1)
        
        # build a factory after e-bay is complete, for armory
        if (
            self.can_afford(UnitTypeId.FACTORY)
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.amount == 1
            and self.structures(UnitTypeId.FACTORY).amount == 0
        ):
            map_center: Point2 = self.game_info.map_center
            target: Point2 = self.start_location.towards(
                map_center, 
                distance=4)
            await self.build(
                UnitTypeId.FACTORY, 
                near=target, 
                placement_step=1)
        
        # build an armory after the e-bay & factory are complete        
        if (
            self.can_afford(UnitTypeId.ARMORY)
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.amount == 1
            and self.structures(UnitTypeId.FACTORY).ready.amount == 1
            and self.structures(UnitTypeId.ARMORY).amount == 0
        ):
            map_center: Point2 = self.game_info.map_center
            target: Point2 = self.start_location.towards(
                map_center, 
                distance=4)
            await self.build(
                UnitTypeId.ARMORY, 
                near=target, 
                placement_step=1)
        
        # research +1 attack upgrades
        w_up: UpgradeId = UpgradeId.TERRANINFANTRYWEAPONSLEVEL1
        if (
            self.already_pending_upgrade(w_up) == 0
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.idle.amount == 1
            and self.can_afford(w_up)
        ):
            self.research(w_up)
        
        # research +1 defense upgrades
        d_up: UpgradeId = UpgradeId.TERRANINFANTRYARMORSLEVEL1
        if (
            self.already_pending_upgrade(d_up) == 0
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.idle.amount == 1
            and self.can_afford(d_up)
        ):
            self.research(d_up)
            
        # research +2 attack upgrades
        w2_up: UpgradeId = UpgradeId.TERRANINFANTRYWEAPONSLEVEL2
        if (
            self.already_pending_upgrade(w2_up) == 0
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.idle.amount == 1
            and self.can_afford(w2_up)
        ):
            self.research(w2_up)
        
        # research +2 def upgrades
        d2_up: UpgradeId = UpgradeId.TERRANINFANTRYARMORSLEVEL2
        if (
            self.already_pending_upgrade(d2_up) == 0
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.idle.amount == 1
            and self.can_afford(d2_up)
        ):
            self.research(d2_up)
        
        # research +3 attack upgrades
        w3_up: UpgradeId = UpgradeId.TERRANINFANTRYWEAPONSLEVEL3
        if (
            self.already_pending_upgrade(w3_up) == 0
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.idle.amount == 1
            and self.can_afford(w3_up)
        ):
            self.research(w3_up)
        
        # research +3 def upgrades
        d3_up: UpgradeId = UpgradeId.TERRANINFANTRYARMORSLEVEL3
        if (
            self.already_pending_upgrade(d3_up) == 0
            and self.structures(UnitTypeId.ENGINEERINGBAY).ready.idle.amount == 1
            and self.can_afford(d3_up)
        ):
            self.research(d3_up)
            
        # research combat shield upgrade - BUGGED
         
        # BUG: c_shield has no 'exact_id' when queried from:
        #      self._game_data.upgrades[upgrade_type.value].research_ability
        #      in method:
        #      self.already_pending_upgrade(c_shield)
        
        # BUG: 'Could not find upgrade UpgradeId.COMBATSHIELD in 'research from'-dictionary'
        #       in method:
        #       self.research(c_shield)
        
        # NOTE: looks like we have to manually translate UpgradeId -> AbilityId,
        #       so we gotta go deeper in api and call what we need...
        
        # TODO: currently doesn't work... fix this
        
#        c_shield: UpgradeId = UpgradeId.COMBATSHIELD
#        if (
#            self.researched_combat_shield == False
#            and self.can_afford(c_shield)
#        ):
#            for rax in self.structures(UnitTypeId.BARRACKS).filter(lambda b: b.has_techlab).ready:
#                self.do(
#                    UnitCommand(AbilityId.RESEARCH_COMBATSHIELD, rax),
#                    subtract_cost=True
#                )
#                self.researched_combat_shield = True
#                break
            
        # build marine & marauders
        # NOTE: build 2 marine at a time out of reactor-rax,
        #       and 1 marauder at a time out of techlab-rax
        # NOTE: not using self.can_afford(<unit>) for reactor check b/c
        #       we need 2x marines, not just one...
        # NOTE: reactor will only train in batches of 2, not single marines...
        # #TODO: (minor) is there a better way to train two marines?
        for rax in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if rax.has_reactor and self.minerals > 100:
                rax.train(UnitTypeId.MARINE)
                rax.train(UnitTypeId.MARINE)
            if rax.has_techlab and self.can_afford(UnitTypeId.MARAUDER):
                rax.train(UnitTypeId.MARAUDER)
            if not (rax.has_reactor or rax.has_techlab) and self.can_afford(UnitTypeId.MARINE):
                rax.train(UnitTypeId.MARINE)

        # attack enemy base with waves of marine-marauder
        # NOTE: assume there is at least one enemy start location?
        # NOTE2: use of '.idle' is IMPORTANT! this allows us to 
        #        send units in batches, since units simply sitting 
        #        around will be idle and ones attacking 
        #        the enemy base won't be selected...
        marines: Units = self.units(UnitTypeId.MARINE).idle
        marauders: Units = self.units(UnitTypeId.MARAUDER).idle
        if marines.amount > 10 and marauders.amount > 10:
            target: Point2 = self.enemy_start_locations[0].position
            for unit in marines:
                unit.attack(target)
            for unit in marauders:
                unit.attack(target)
        
    async def on_start(self):
        # NOTE: sc2 updates 22.4 frames/sec on 'faster'
        self.client.game_step: int = 22
        
        # keep track of rax-reactor and rax-tech-lab count
        self.rax_reactor = 0
        self.rax_techlab = 0
        
        # keep track of combat shield upgrade, broken, see TODO above...
        self.researched_combat_shield = False
        
        # 2nd ref check
        # TODO: is there a better way to handle finding 2nd non-built-on vespene geyser?
        self.built_first_ref = False
        
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
    [ Bot(Race.Terran, Basic()), Computer(Race.Zerg, Difficulty.Medium) ],
    realtime=True
)

