import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId
from sc2.position import Point2, Point3
from sc2.unit import Unit
from sc2.units import Units
from sc2.player import Bot, Computer

class Basic(sc2.BotAI):
    def __init__(self):
        self.distance_calculation_method: int = 2
        self.raw_affects_selection: bool = True
        self.unit_command_uses_self_do: bool = False # TODO: what is this for???
        
        self.logic: List[Callable[[], None]] = [self.progression_loop]
        
        self.is_attacking = False

    async def progression_loop(self):    
        # train SCVs until we hit mineral field limit
        cc: Unit = self.townhalls(UnitTypeId.COMMANDCENTER).first
        if (
            self.can_afford(UnitTypeId.SCV) 
            and cc.is_idle 
            and self.workers.amount < 16 # TODO: how to check workers only on minerals?
            and self.supply_left >= 1
        ): 
            cc.train(UnitTypeId.SCV)
            
        # build depots as necessary, building more w/ more supply
        if (
            self.supply_left <= max(2, int(self.supply_used/20)) 
            and self.already_pending(UnitTypeId.SUPPLYDEPOT) < max(1, int(self.supply_used/20))
        ):
            map_center: Point2 = self.game_info.map_center
            position_towards_map_center: Point2 = self.start_location.towards(map_center, distance=5)
            await self.build(UnitTypeId.SUPPLYDEPOT, near=position_towards_map_center, placement_step=1)
        
        # iterate thru all depots and make sure they are LOWERED
        for depo in self.structures(UnitTypeId.SUPPLYDEPOT).ready:
            depo(AbilityId.MORPH_SUPPLYDEPOT_LOWER)
        
        # route idle workers back to minerals
        for scv in self.workers.idle:
            cc: Unit = self.townhalls(UnitTypeId.COMMANDCENTER).first
            scv.smart(self.mineral_field.closest_to(cc))
            
        # build up to 6 rax
        # NOTE: we can get away with not checking self.already_pending(<barracks>) because
        #       we don't accumulate enough minerals that quickly anyway...
        # NOTE2: self.already_pending is only for queued buildings, self.buildings(<barracks>)
        #        will accumulate all constructed AND currently-being-built buildings as well
        if (
            self.can_afford(UnitTypeId.BARRACKS)
            and self.structures(UnitTypeId.BARRACKS).amount < 6
        ):
            map_center: Point2 = self.game_info.map_center
            position_towards_map_center: Point2 = self.start_location.towards(map_center, distance=5)
            await self.build(UnitTypeId.BARRACKS, near=position_towards_map_center, placement_step=1)
            
        # TODO: set rally points of READY rax to...?
            
        # build marines forever! >:)
        for rax in self.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.can_afford(UnitTypeId.MARINE):
                rax.train(UnitTypeId.MARINE)

        # attack enemy base with waves of 15 units
        # NOTE: assume there is at least one enemy start location?
        # NOTE2: use of '.idle' is IMPORTANT! this allows us to send marines in batches,
        #        since units simply sitting around will be idle and ones attacking the enemy base
        #        won't be selectd...
        marines: Units = self.units(UnitTypeId.MARINE).idle
        if marines.amount > 15:
            target: Point2 = self.enemy_start_locations[0].position # type(self.enemy_start_locations) = List[Point2]
            for marine in marines:
                marine.attack(target)
                

    async def on_start(self):
        self.client.game_step: int = 60 # NOTE: every 60 frames !

    async def on_step(self, iteration):
        curr_logic: Callable[[],None] = self.logic[0]
        await curr_logic()
        
# [<AIBuild.RandomBuild: 1>, <AIBuild.Rush: 2>, <AIBuild.Timing: 3>, <AIBuild.Power: 4>, <AIBuild.Macro: 5>, <AIBuild.Air: 6>]
# [<Difficulty.VeryEasy: 1>, <Difficulty.Easy: 2>, <Difficulty.Medium: 3>, <Difficulty.MediumHard: 4>, <Difficulty.Hard: 5>, <Difficulty.Harder: 6>, <Difficulty.VeryHard: 7>, <Difficulty.CheatVision: 8>, <Difficulty.CheatMoney: 9>, <Difficulty.CheatInsane: 10>]

run_game(
    maps.get('Acropolis LE'),
    [ Bot(Race.Terran, Basic()), Computer(Race.Protoss, Difficulty.Medium) ],
    realtime=True
)

