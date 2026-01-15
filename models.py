"""Data models for the PlayoffPurge app."""
from dataclasses import dataclass
from typing import List


@dataclass
class Player:
    """Represents a player on a team's roster."""
    position: str
    player_name: str
    team: str  # NFL team abbreviation
    points: float
    projected_points: float = 0.0
    roster_eligibility: str = ""  # e.g., "WR/FLEX", "RB/FLEX", "QB"
    status: str = "active"
    
    def __post_init__(self):
        """Validate and normalize data."""
        try:
            self.points = float(self.points)
        except (ValueError, TypeError):
            self.points = 0.0
        
        try:
            self.projected_points = float(self.projected_points) if self.projected_points else 0.0
        except (ValueError, TypeError):
            self.projected_points = 0.0
        
        # Default roster_eligibility: RB/WR/TE can fill FLEX
        if not self.roster_eligibility or self.roster_eligibility.strip() == "":
            pos = self.position.upper()
            if pos in ["RB", "WR", "TE"]:
                self.roster_eligibility = f"{pos}/FLEX"
            else:
                self.roster_eligibility = pos
    
    def get_eligible_positions(self) -> list:
        """
        Get list of positions this player can fill.
        
        Returns:
            List of position strings (e.g., ["WR", "FLEX"] for "WR/FLEX")
        """
        if "/" in self.roster_eligibility:
            return self.roster_eligibility.split("/")
        return [self.roster_eligibility]
    
    def can_fill_position(self, required_position: str) -> bool:
        """
        Check if this player can fill a specific roster position.
        
        Args:
            required_position: Position requirement (e.g., "FLEX", "SUPERFLEX", "WR", "RB")
            
        Returns:
            True if player is eligible for this position
        """
        req_pos = required_position.upper()
        player_pos = self.position.upper()
        
        # SUPERFLEX can be filled by QB, RB, WR, or TE (any offensive position)
        if req_pos == "SUPERFLEX":
            return player_pos in ["QB", "RB", "WR", "TE"]
        
        # FLEX can be filled by RB, WR, or TE
        if req_pos == "FLEX":
            return player_pos in ["RB", "WR", "TE"]
        
        # Check against player's roster_eligibility
        eligible_positions = self.get_eligible_positions()
        return req_pos in [pos.upper() for pos in eligible_positions]


@dataclass
class Team:
    """Represents a fantasy team."""
    team_id: int
    owner_name: str
    team_name: str
    seed: int
    status: str  # active, eliminated, champion
    total_points: float
    current_week: str
    roster: List[Player] = None
    
    def __post_init__(self):
        """Validate and normalize data."""
        try:
            self.team_id = int(self.team_id)
            self.seed = int(self.seed)
            self.total_points = float(self.total_points)
        except (ValueError, TypeError):
            self.total_points = 0.0
        
        if self.roster is None:
            self.roster = []
    
    @property
    def is_active(self) -> bool:
        """Check if team is still active in the league."""
        return self.status.lower() == "active"
    
    @property
    def is_eliminated(self) -> bool:
        """Check if team has been eliminated."""
        return self.status.lower() == "eliminated"
    
    @property
    def is_champion(self) -> bool:
        """Check if team is the champion."""
        return self.status.lower() == "champion"
    
    @property
    def status_emoji(self) -> str:
        """Get emoji representation of status."""
        if self.is_active:
            return "✅"
        elif self.is_eliminated:
            return "❌"
        elif self.is_champion:
            return "🏆"
        return "❓"
    
    @property
    def total_projected_points(self) -> float:
        """Calculate total projected points from roster."""
        if not self.roster:
            return 0.0
        return sum(player.projected_points for player in self.roster)


@dataclass
class LeagueMeta:
    """Represents league metadata."""
    league_name: str
    current_week: str
    last_updated: str
    
    def __post_init__(self):
        """Set defaults if needed."""
        if not self.league_name:
            self.league_name = "PlayoffPurge"
        if not self.current_week:
            self.current_week = "Week 18"
        if not self.last_updated:
            self.last_updated = "Unknown"


@dataclass
class RosterRequirement:
    """Represents weekly roster requirements."""
    week: str
    teams_left: int
    positions_required: str
    payout: str
    
    def __post_init__(self):
        """Validate and normalize data."""
        try:
            self.teams_left = int(self.teams_left)
        except (ValueError, TypeError):
            self.teams_left = 0


@dataclass
class AvailablePlayer:
    """Represents an available player in the draft pool."""
    player_id: str  # Changed to str to support FanDuel hyphenated IDs
    player_name: str
    position: str
    nfl_team: str
    bye_week: int
    status: str  # available, drafted
    roster_eligibility: str = ""  # e.g., "WR/FLEX", "RB/FLEX", "QB"
    fppg: float = None  # Fantasy Points Per Game from PlayerPool_FanDuel
    opponent: str = None  # Opponent team from PlayerPool_FanDuel
    
    def __post_init__(self):
        """Validate and normalize data."""
        try:
            self.player_id = str(self.player_id)  # Keep as string
            self.bye_week = int(self.bye_week) if self.bye_week else 0
            if self.fppg is not None:
                self.fppg = float(self.fppg)
        except (ValueError, TypeError):
            self.bye_week = 0
        
        # Default roster_eligibility: RB/WR/TE can fill FLEX
        if not self.roster_eligibility or self.roster_eligibility.strip() == "":
            pos = self.position.upper()
            if pos in ["RB", "WR", "TE"]:
                self.roster_eligibility = f"{pos}/FLEX"
            else:
                self.roster_eligibility = pos
    
    @property
    def is_available(self) -> bool:
        """Check if player is available to draft."""
        return self.status.lower() == "available"
    
    def get_eligible_positions(self) -> list:
        """Get list of positions this player can fill."""
        if "/" in self.roster_eligibility:
            return self.roster_eligibility.split("/")
        return [self.roster_eligibility]
    
    def can_fill_position(self, required_position: str) -> bool:
        """
        Check if this player can fill a specific roster position.
        
        Args:
            required_position: Position requirement (e.g., "FLEX", "SUPERFLEX", "WR", "RB")
            
        Returns:
            True if player is eligible for this position
        """
        req_pos = required_position.upper()
        player_pos = self.position.upper()
        
        # SUPERFLEX can be filled by QB, RB, WR, or TE (any offensive position)
        if req_pos == "SUPERFLEX":
            return player_pos in ["QB", "RB", "WR", "TE"]
        
        # FLEX can be filled by RB, WR, or TE
        if req_pos == "FLEX":
            return player_pos in ["RB", "WR", "TE"]
        
        # Check against player's roster_eligibility
        eligible_positions = self.get_eligible_positions()
        return req_pos in [pos.upper() for pos in eligible_positions]


@dataclass
class DraftState:
    """Represents the current state of the draft."""
    current_round: int
    current_pick: int
    draft_started: bool
    draft_complete: bool
    last_pick_time: str
    
    def __post_init__(self):
        """Validate and normalize data."""
        # Parse current_round separately
        try:
            self.current_round = int(self.current_round)
        except (ValueError, TypeError):
            self.current_round = 1
        
        # Parse current_pick separately
        try:
            self.current_pick = int(self.current_pick)
        except (ValueError, TypeError):
            self.current_pick = 1
        
        # Parse boolean fields (don't reset on integer parse errors)
        self.draft_started = str(self.draft_started).lower() in ('true', '1', 'yes')
        self.draft_complete = str(self.draft_complete).lower() in ('true', '1', 'yes')


@dataclass
class DraftPick:
    """Represents a pick in the draft order."""
    round: int
    pick: int
    team_id: int
    owner_name: str
    status: str  # completed, current, upcoming
    player_id: int = 0
    player_name: str = ""
    
    def __post_init__(self):
        """Validate and normalize data."""
        try:
            self.round = int(self.round)
            self.pick = int(self.pick)
            self.team_id = int(self.team_id)
            self.player_id = int(self.player_id) if self.player_id else 0
        except (ValueError, TypeError):
            pass
    
    @property
    def is_current(self) -> bool:
        """Check if this is the current pick."""
        return self.status.lower() == "current"
    
    @property
    def is_completed(self) -> bool:
        """Check if this pick has been made."""
        return self.status.lower() == "completed"
