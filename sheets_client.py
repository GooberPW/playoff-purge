"""Google Sheets client with caching for PlayoffPurge."""
import logging
import time
from typing import Dict, List, Optional

from cachetools import TTLCache
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import settings
from models import (
    AvailablePlayer, DraftPick, DraftState, LeagueMeta, 
    Player, RosterRequirement, Team
)

logger = logging.getLogger(__name__)


class SheetsClient:
    """Client for interacting with Google Sheets API with caching."""
    
    def __init__(self):
        """Initialize the Sheets client."""
        self.sheet_id = settings.google_sheet_id
        self.service = None
        self._cache = TTLCache(maxsize=100, ttl=settings.cache_ttl_seconds)
        self._last_request_time = 0
        self._min_request_interval = 0.5  # Rate limiting: 2 req/sec (safe for batch operations)
        
    def _build_service(self):
        """Build and cache the Sheets API service."""
        if self.service is None:
            try:
                credentials_path = settings.get_credentials_path()
                credentials = service_account.Credentials.from_service_account_file(
                    credentials_path,
                    scopes=['https://www.googleapis.com/auth/spreadsheets']
                )
                self.service = build('sheets', 'v4', credentials=credentials)
                logger.info("Successfully initialized Google Sheets API client")
            except Exception as e:
                logger.error(f"Failed to initialize Sheets API: {e}")
                raise
        return self.service
    
    def _rate_limit(self):
        """Simple rate limiting to avoid API quota issues."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()
    
    def _get_range(self, range_name: str, retry_count: int = 3) -> List[List]:
        """
        Get data from a specific range with retry logic.
        
        Args:
            range_name: Sheet range (e.g., "Teams!A2:G100")
            retry_count: Number of retries on failure
            
        Returns:
            List of rows (each row is a list of values)
        """
        service = self._build_service()
        
        for attempt in range(retry_count):
            try:
                self._rate_limit()
                result = service.spreadsheets().values().get(
                    spreadsheetId=self.sheet_id,
                    range=range_name
                ).execute()
                
                values = result.get('values', [])
                logger.info(f"Successfully fetched {len(values)} rows from {range_name}")
                return values
                
            except HttpError as e:
                if e.resp.status in [429, 500, 503]:  # Rate limit or server error
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"API error {e.resp.status}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"API error: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error fetching {range_name}: {e}")
                if attempt == retry_count - 1:
                    raise
                time.sleep(2 ** attempt)
        
        return []
    
    def _batch_get_ranges(self, ranges: List[str], retry_count: int = 3) -> Dict[str, List[List]]:
        """
        Fetch multiple ranges in ONE API call using batchGet.
        
        Args:
            ranges: List of range names (e.g., ["Teams!A2:G100", "Rosters!A2:I500"])
            retry_count: Number of retries on failure
            
        Returns:
            Dictionary mapping range name to list of rows
        """
        service = self._build_service()
        
        for attempt in range(retry_count):
            try:
                self._rate_limit()
                result = service.spreadsheets().values().batchGet(
                    spreadsheetId=self.sheet_id,
                    ranges=ranges
                ).execute()
                
                # Build dict mapping range to values
                batch_data = {}
                for value_range in result.get('valueRanges', []):
                    range_name = value_range.get('range', '')
                    values = value_range.get('values', [])
                    batch_data[range_name] = values
                    logger.info(f"Batch fetched {len(values)} rows from {range_name}")
                
                logger.info(f"Successfully batch fetched {len(batch_data)} ranges in ONE API call")
                return batch_data
                
            except HttpError as e:
                if e.resp.status in [429, 500, 503]:
                    wait_time = 2 ** attempt
                    logger.warning(f"Batch API error {e.resp.status}, retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Batch API error: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error in batch fetch: {e}")
                if attempt == retry_count - 1:
                    raise
                time.sleep(2 ** attempt)
        
        return {}
    
    def get_league_meta(self, use_cache: bool = True) -> LeagueMeta:
        """
        Get league metadata from the League_Meta tab.
        
        Expected format:
        | key           | value                |
        |---------------|----------------------|
        | league_name   | PlayoffPurge 2025    |
        | current_week  | Week 18              |
        | last_updated  | 2025-01-05 14:30:00  |
        """
        cache_key = "league_meta"
        
        if use_cache and cache_key in self._cache:
            logger.debug("Using cached league meta")
            return self._cache[cache_key]
        
        try:
            rows = self._get_range("League_Meta!A2:B10")
            
            # Parse key-value pairs
            meta_dict = {}
            for row in rows:
                if len(row) >= 2:
                    key = row[0].strip().lower().replace(" ", "_")
                    value = row[1].strip()
                    meta_dict[key] = value
            
            meta = LeagueMeta(
                league_name=meta_dict.get("league_name", "PlayoffPurge"),
                current_week=meta_dict.get("current_week", "Week 18"),
                last_updated=meta_dict.get("last_updated", "Unknown")
            )
            
            self._cache[cache_key] = meta
            return meta
            
        except Exception as e:
            logger.error(f"Error fetching league meta: {e}")
            # Return default meta on error
            return LeagueMeta(
                league_name="PlayoffPurge",
                current_week="Week 18",
                last_updated="Unknown"
            )
    
    def get_teams(self, use_cache: bool = True) -> List[Team]:
        """
        Get all teams from the Teams tab.
        
        Expected format:
        | team_id | owner_name | team_name | seed | status | total_points | current_week |
        """
        cache_key = "teams"
        
        if use_cache and cache_key in self._cache:
            logger.debug("Using cached teams")
            return self._cache[cache_key]
        
        try:
            rows = self._get_range("Teams!A2:G100")
            
            teams = []
            for row in rows:
                if len(row) < 7:
                    logger.warning(f"Skipping incomplete row: {row}")
                    continue
                
                try:
                    team = Team(
                        team_id=row[0],
                        owner_name=row[1],
                        team_name=row[2],
                        seed=row[3],
                        status=row[4],
                        total_points=row[5],
                        current_week=row[6]
                    )
                    teams.append(team)
                except Exception as e:
                    logger.warning(f"Error parsing team row {row}: {e}")
                    continue
            
            # Sort by seed
            teams.sort(key=lambda t: t.seed)
            
            self._cache[cache_key] = teams
            logger.info(f"Loaded {len(teams)} teams")
            return teams
            
        except Exception as e:
            logger.error(f"Error fetching teams: {e}")
            return []
    
    def get_roster(self, team_id: int, use_cache: bool = True) -> List[Player]:
        """
        Get roster for a specific team from the Rosters tab.
        
        Expected format:
        | team_id | week | position | player_name | team | points | projected_points | status |
        """
        cache_key = f"roster_{team_id}"
        
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached roster for team {team_id}")
            return self._cache[cache_key]
        
        try:
            # Get all rosters (now includes projected_points + roster_eligibility)
            rows = self._get_range("Rosters!A2:I500")
            
            players = []
            for row in rows:
                if len(row) < 6:
                    continue
                
                # Check if this row belongs to our team
                try:
                    row_team_id = int(row[0])
                    if row_team_id != team_id:
                        continue
                    
                    player = Player(
                        position=row[2],
                        player_name=row[3],
                        team=row[4],
                        points=row[5],
                        projected_points=row[6] if len(row) > 6 else 0.0,
                        roster_eligibility=row[8] if len(row) > 8 else "",
                        status=row[7] if len(row) > 7 else "active"
                    )
                    players.append(player)
                except Exception as e:
                    logger.warning(f"Error parsing roster row {row}: {e}")
                    continue
            
            # Sort by position order (QB, RB, WR, TE, FLEX, K, DST, SUPERFLEX)
            position_order = {
                "QB": 0, "SUPERFLEX": 1, "RB": 2, "WR": 3, 
                "TE": 4, "FLEX": 5, "K": 6, "DST": 7, "DEF": 7
            }
            players.sort(key=lambda p: position_order.get(p.position.upper(), 99))
            
            self._cache[cache_key] = players
            logger.info(f"Loaded {len(players)} players for team {team_id}")
            return players
            
        except Exception as e:
            logger.error(f"Error fetching roster for team {team_id}: {e}")
            return []
    
    def get_teams_with_rosters(self, use_cache: bool = True) -> List[Team]:
        """
        Get all teams with their rosters loaded.
        Optimized to fetch all rosters in ONE API call instead of per-team.
        """
        teams = self.get_teams(use_cache=use_cache)
        league_meta = self.get_league_meta(use_cache=use_cache)
        
        # Fetch all rosters for current week in ONE call
        all_rosters = self.get_rosters_by_week(
            league_meta.current_week,
            use_cache=use_cache
        )
        
        # Assign rosters to teams
        for team in teams:
            team.roster = all_rosters.get(team.team_id, [])
        
        logger.info(f"Loaded rosters for {len(teams)} teams in batch")
        return teams
    
    def get_roster_requirements(self, use_cache: bool = True) -> List[RosterRequirement]:
        """
        Get all roster requirements from the Roster_Requirements tab.
        
        Expected format:
        | week | teams_left | positions_required | payout |
        """
        cache_key = "roster_requirements"
        
        if use_cache and cache_key in self._cache:
            logger.debug("Using cached roster requirements")
            return self._cache[cache_key]
        
        try:
            rows = self._get_range("Roster_Requirements!A2:D10")
            
            requirements = []
            for row in rows:
                if len(row) < 4:
                    logger.warning(f"Skipping incomplete row: {row}")
                    continue
                
                try:
                    req = RosterRequirement(
                        week=row[0],
                        teams_left=row[1],
                        positions_required=row[2],
                        payout=row[3]
                    )
                    requirements.append(req)
                except Exception as e:
                    logger.warning(f"Error parsing requirement row {row}: {e}")
                    continue
            
            self._cache[cache_key] = requirements
            logger.info(f"Loaded {len(requirements)} roster requirements")
            return requirements
            
        except Exception as e:
            logger.error(f"Error fetching roster requirements: {e}")
            return []
    
    def get_roster_requirement_for_week(self, week: str, use_cache: bool = True) -> Optional[RosterRequirement]:
        """
        Get roster requirement for a specific week.
        
        Args:
            week: Week name (e.g., "Week 18", "Wildcard")
            use_cache: Whether to use cached data
            
        Returns:
            RosterRequirement if found, None otherwise
        """
        requirements = self.get_roster_requirements(use_cache=use_cache)
        
        for req in requirements:
            if req.week.strip().lower() == week.strip().lower():
                return req
        
        logger.warning(f"No roster requirement found for week: {week}")
        return None
    
    def get_rosters_by_week(self, week: str, use_cache: bool = True) -> Dict[int, List[Player]]:
        """
        Get all rosters for a specific week, organized by team_id.
        
        Args:
            week: Week name (e.g., "Week 18")
            use_cache: Whether to use cached data
            
        Returns:
            Dictionary mapping team_id to list of players for that week
        """
        cache_key = f"rosters_week_{week.lower().replace(' ', '_')}"
        
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached rosters for week {week}")
            return self._cache[cache_key]
        
        try:
            # Get all rosters (now includes projected_points + roster_eligibility)
            rows = self._get_range("Rosters!A2:I500")
            
            # Organize by team_id
            rosters_by_team = {}
            
            for row in rows:
                if len(row) < 6:
                    continue
                
                try:
                    row_team_id = int(row[0])
                    row_week = row[1].strip()
                    
                    # Only include players from the specified week
                    if row_week.lower() != week.strip().lower():
                        continue
                    
                    player = Player(
                        position=row[2],
                        player_name=row[3],
                        team=row[4],
                        points=row[5],
                        projected_points=row[6] if len(row) > 6 else 0.0,
                        roster_eligibility=row[8] if len(row) > 8 else "",
                        status=row[7] if len(row) > 7 else "active"
                    )
                    
                    if row_team_id not in rosters_by_team:
                        rosters_by_team[row_team_id] = []
                    
                    rosters_by_team[row_team_id].append(player)
                    
                except Exception as e:
                    logger.warning(f"Error parsing roster row {row}: {e}")
                    continue
            
            # Sort players within each team by position
            position_order = {
                "QB": 0, "SUPERFLEX": 1, "RB": 2, "WR": 3, 
                "TE": 4, "FLEX": 5, "K": 6, "DST": 7, "DEF": 7
            }
            
            for team_id in rosters_by_team:
                rosters_by_team[team_id].sort(
                    key=lambda p: position_order.get(p.position.upper(), 99)
                )
            
            self._cache[cache_key] = rosters_by_team
            logger.info(f"Loaded rosters for {len(rosters_by_team)} teams in week {week}")
            return rosters_by_team
            
        except Exception as e:
            logger.error(f"Error fetching rosters for week {week}: {e}")
            return {}
    
    def get_available_players(self, use_cache: bool = True, position_filter: Optional[str] = None) -> List[AvailablePlayer]:
        """
        Get available players from the Available_Players tab with enhanced data from PlayerPool_FanDuel.
        
        Expected format:
        Available_Players: | player_id | player_name | position | nfl_team | bye_week | status |
        PlayerPool_FanDuel: | player_id | ... | FPPG | Opponent | ... |
        
        Args:
            use_cache: Whether to use cached data
            position_filter: Optional position to filter by (e.g., "QB", "RB")
            
        Returns:
            List of AvailablePlayer objects with FPPG and opponent data
        """
        cache_key = f"available_players_{position_filter or 'all'}"
        
        if use_cache and cache_key in self._cache:
            logger.debug(f"Using cached available players (filter: {position_filter})")
            return self._cache[cache_key]
        
        try:
            # Get available players (including roster_eligibility in column G)
            rows = self._get_range("Available_Players!A2:G500")
            
            # Get enhanced data from PlayerPool_FanDuel (player_id, FPPG, Opponent)
            try:
                # First get the header row to find column indices
                header_row = self._get_range("PlayerPool_FanDuel!A1:Z1")
                fppg_col_idx = None
                opponent_col_idx = None
                
                if header_row and len(header_row) > 0:
                    headers = header_row[0]
                    for idx, header in enumerate(headers):
                        header_lower = str(header).lower().strip()
                        if header_lower == 'fppg':
                            fppg_col_idx = idx
                        elif header_lower == 'opponent':
                            opponent_col_idx = idx
                
                logger.info(f"Found FPPG at column {fppg_col_idx}, Opponent at column {opponent_col_idx}")
                
                pool_rows = self._get_range("PlayerPool_FanDuel!A2:Z500")
                # Build lookup dict {player_id: {fppg, opponent}}
                pool_data = {}
                for pool_row in pool_rows:
                    if len(pool_row) > 0:
                        p_id = str(pool_row[0])
                        fppg = None
                        opponent = None
                        
                        # Get FPPG from the identified column
                        if fppg_col_idx is not None and len(pool_row) > fppg_col_idx:
                            try:
                                fppg_val = pool_row[fppg_col_idx]
                                if fppg_val:
                                    fppg = float(fppg_val)
                            except:
                                pass
                        
                        # Get Opponent from the identified column
                        if opponent_col_idx is not None and len(pool_row) > opponent_col_idx:
                            opponent_val = pool_row[opponent_col_idx]
                            if opponent_val:
                                opponent = str(opponent_val).strip()
                        
                        pool_data[p_id] = {"fppg": fppg, "opponent": opponent}
            except Exception as e:
                logger.warning(f"Could not load PlayerPool_FanDuel data: {e}")
                pool_data = {}
            
            players = []
            for row in rows:
                if len(row) < 6:
                    continue
                
                try:
                    player = AvailablePlayer(
                        player_id=row[0],
                        player_name=row[1],
                        position=row[2],
                        nfl_team=row[3],
                        bye_week=row[4],
                        status=row[5],
                        roster_eligibility=row[6] if len(row) > 6 else ""
                    )
                    
                    # Add enhanced data if available
                    enhanced = pool_data.get(str(player.player_id), {})
                    player.fppg = enhanced.get("fppg")
                    player.opponent = enhanced.get("opponent")
                    
                    # Apply position filter if specified
                    if position_filter and player.position.upper() != position_filter.upper():
                        continue
                    
                    players.append(player)
                except Exception as e:
                    logger.warning(f"Error parsing player row {row}: {e}")
                    continue
            
            self._cache[cache_key] = players
            logger.info(f"Loaded {len(players)} available players")
            return players
            
        except Exception as e:
            logger.error(f"Error fetching available players: {e}")
            return []
    
    def get_draft_state(self, use_cache: bool = False) -> DraftState:
        """
        Get current draft state from the Draft_State tab.
        
        Expected format (key-value pairs):
        | key              | value |
        |------------------|-------|
        | current_round    | 1     |
        | current_pick     | 1     |
        | draft_started    | true  |
        | draft_complete   | false |
        | last_pick_time   | ...   |
        
        Note: Draft state should not be cached heavily as it changes frequently
        """
        cache_key = "draft_state"
        
        if use_cache and cache_key in self._cache:
            logger.debug("Using cached draft state")
            return self._cache[cache_key]
        
        try:
            rows = self._get_range("Draft_State!A2:B10")
            
            state_dict = {}
            for row in rows:
                if len(row) >= 2:
                    key = row[0].strip().lower().replace(" ", "_")
                    value = row[1].strip()
                    state_dict[key] = value
            
            state = DraftState(
                current_round=state_dict.get("current_round", "1"),
                current_pick=state_dict.get("current_pick", "1"),
                draft_started=state_dict.get("draft_started", "false"),
                draft_complete=state_dict.get("draft_complete", "false"),
                last_pick_time=state_dict.get("last_pick_time", "")
            )
            
            self._cache[cache_key] = state
            return state
            
        except Exception as e:
            logger.error(f"Error fetching draft state: {e}")
            return DraftState(
                current_round=1,
                current_pick=1,
                draft_started=False,
                draft_complete=False,
                last_pick_time=""
            )
    
    def get_draft_order(self, use_cache: bool = True) -> List[DraftPick]:
        """
        Get draft order from the Draft_Order tab.
        
        Expected format:
        | round | pick | team_id | owner_name | status | player_id | player_name |
        """
        cache_key = "draft_order"
        
        if use_cache and cache_key in self._cache:
            logger.debug("Using cached draft order")
            return self._cache[cache_key]
        
        try:
            rows = self._get_range("Draft_Order!A2:G100")
            
            picks = []
            for row in rows:
                if len(row) < 5:
                    continue
                
                try:
                    pick = DraftPick(
                        round=row[0],
                        pick=row[1],
                        team_id=row[2],
                        owner_name=row[3],
                        status=row[4],
                        player_id=row[5] if len(row) > 5 else 0,
                        player_name=row[6] if len(row) > 6 else ""
                    )
                    picks.append(pick)
                except Exception as e:
                    logger.warning(f"Error parsing draft pick row {row}: {e}")
                    continue
            
            self._cache[cache_key] = picks
            logger.info(f"Loaded {len(picks)} draft picks")
            return picks
            
        except Exception as e:
            logger.error(f"Error fetching draft order: {e}")
            return []
    
    def get_current_pick(self, use_cache: bool = False) -> Optional[DraftPick]:
        """Get the current pick from the draft order."""
        picks = self.get_draft_order(use_cache=use_cache)
        
        for pick in picks:
            if pick.is_current:
                return pick
        
        logger.warning("No current pick found in draft order")
        return None
    
    def get_all_draft_data(self, use_cache: bool = True, force_fresh_draft_state: bool = False) -> dict:
        """
        Fetch ALL draft-related data in ONE API call using batchGet.
        This dramatically reduces API calls and improves performance.
        
        Args:
            use_cache: Whether to use cached data for static content
            force_fresh_draft_state: If True, fetches draft state & current pick fresh
                                     even if other data is cached (for real-time updates)
            
        Returns:
            Dictionary with all parsed draft data
        """
        cache_key = "all_draft_data"
        
        # Two-tier caching: Use cached data but refresh draft state if requested
        if use_cache and cache_key in self._cache and force_fresh_draft_state:
            logger.info("Using cached data with fresh draft state refresh")
            cached_data = self._cache[cache_key].copy()
            
            # Fetch only draft-critical data fresh (2 quick API calls)
            try:
                fresh_draft_state = self.get_draft_state(use_cache=False)
                fresh_current_pick = self.get_current_pick(use_cache=False)
                
                # Update cached data with fresh draft info
                cached_data['draft_state'] = fresh_draft_state
                cached_data['current_pick'] = fresh_current_pick
                
                logger.info("✅ Refreshed draft state while using cached data")
                return cached_data
            except Exception as e:
                logger.warning(f"Failed to refresh draft state, using fully cached data: {e}")
                return cached_data
        
        if use_cache and cache_key in self._cache:
            logger.debug("Using fully cached all_draft_data")
            return self._cache[cache_key]
        
        try:
            # Fetch ALL ranges in ONE API call!
            logger.info("Fetching all draft data in batch...")
            batch_data = self._batch_get_ranges([
                "League_Meta!A2:B10",
                "Teams!A2:G100",
                "Roster_Requirements!A2:D10",
                "Rosters!A2:I500",
                "Available_Players!A2:G500",
                "PlayerPool_FanDuel!A1:Z500",
                "Draft_State!A2:B10",
                "Draft_Order!A2:G100"
            ])
            
            # Parse League Meta
            league_meta_rows = batch_data.get("League_Meta!A2:B10", [])
            meta_dict = {}
            for row in league_meta_rows:
                if len(row) >= 2:
                    key = row[0].strip().lower().replace(" ", "_")
                    value = row[1].strip()
                    meta_dict[key] = value
            
            league_meta = LeagueMeta(
                league_name=meta_dict.get("league_name", "PlayoffPurge"),
                current_week=meta_dict.get("current_week", "Week 18"),
                last_updated=meta_dict.get("last_updated", "Unknown")
            )
            
            # Parse Teams
            team_rows = batch_data.get("Teams!A2:G100", [])
            teams = []
            for row in team_rows:
                if len(row) >= 7:
                    try:
                        teams.append(Team(
                            team_id=row[0],
                            owner_name=row[1],
                            team_name=row[2],
                            seed=row[3],
                            status=row[4],
                            total_points=row[5],
                            current_week=row[6]
                        ))
                    except Exception as e:
                        logger.warning(f"Error parsing team row: {e}")
            teams.sort(key=lambda t: t.seed)
            
            # Parse Roster Requirements
            req_rows = batch_data.get("Roster_Requirements!A2:D10", [])
            requirements = {}
            for row in req_rows:
                if len(row) >= 4:
                    try:
                        req = RosterRequirement(
                            week=row[0],
                            teams_left=row[1],
                            positions_required=row[2],
                            payout=row[3]
                        )
                        requirements[req.week.strip().lower()] = req
                    except Exception as e:
                        logger.warning(f"Error parsing requirement row: {e}")
            
            # Parse Rosters (all weeks, organized by team_id)
            roster_rows = batch_data.get("Rosters!A2:I500", [])
            rosters_by_team = {}
            for row in roster_rows:
                if len(row) >= 6:
                    try:
                        team_id = int(row[0])
                        week = row[1].strip()
                        player = Player(
                            position=row[2],
                            player_name=row[3],
                            team=row[4],
                            points=row[5],
                            projected_points=row[6] if len(row) > 6 else 0.0,
                            roster_eligibility=row[8] if len(row) > 8 else "",
                            status=row[7] if len(row) > 7 else "active"
                        )
                        player.week = week  # Store week on player for filtering
                        
                        if team_id not in rosters_by_team:
                            rosters_by_team[team_id] = []
                        rosters_by_team[team_id].append(player)
                    except Exception as e:
                        logger.warning(f"Error parsing roster row: {e}")
            
            # Parse Available Players with FPPG data
            player_rows = batch_data.get("Available_Players!A2:G500", [])
            pool_rows = batch_data.get("PlayerPool_FanDuel!A1:Z500", [])
            
            # Find FPPG and Opponent columns
            fppg_col_idx = None
            opponent_col_idx = None
            if pool_rows and len(pool_rows) > 0:
                headers = pool_rows[0]
                for idx, header in enumerate(headers):
                    header_lower = str(header).lower().strip()
                    if header_lower == 'fppg':
                        fppg_col_idx = idx
                    elif header_lower == 'opponent':
                        opponent_col_idx = idx
            
            # Build player pool lookup
            pool_data = {}
            for pool_row in pool_rows[1:]:  # Skip header
                if len(pool_row) > 0:
                    p_id = str(pool_row[0])
                    fppg = None
                    opponent = None
                    
                    if fppg_col_idx is not None and len(pool_row) > fppg_col_idx:
                        try:
                            if pool_row[fppg_col_idx]:
                                fppg = float(pool_row[fppg_col_idx])
                        except:
                            pass
                    
                    if opponent_col_idx is not None and len(pool_row) > opponent_col_idx:
                        if pool_row[opponent_col_idx]:
                            opponent = str(pool_row[opponent_col_idx]).strip()
                    
                    pool_data[p_id] = {"fppg": fppg, "opponent": opponent}
            
            # Parse available players
            available_players = []
            for row in player_rows:
                if len(row) >= 6:
                    try:
                        player = AvailablePlayer(
                            player_id=row[0],
                            player_name=row[1],
                            position=row[2],
                            nfl_team=row[3],
                            bye_week=row[4],
                            status=row[5],
                            roster_eligibility=row[6] if len(row) > 6 else ""
                        )
                        # Add enhanced data
                        enhanced = pool_data.get(str(player.player_id), {})
                        player.fppg = enhanced.get("fppg")
                        player.opponent = enhanced.get("opponent")
                        available_players.append(player)
                    except Exception as e:
                        logger.warning(f"Error parsing available player row: {e}")
            
            # Parse Draft State
            state_rows = batch_data.get("Draft_State!A2:B10", [])
            state_dict = {}
            for row in state_rows:
                if len(row) >= 2:
                    key = row[0].strip().lower().replace(" ", "_")
                    value = row[1].strip()
                    state_dict[key] = value
            
            draft_state = DraftState(
                current_round=state_dict.get("current_round", "1"),
                current_pick=state_dict.get("current_pick", "1"),
                draft_started=state_dict.get("draft_started", "false"),
                draft_complete=state_dict.get("draft_complete", "false"),
                last_pick_time=state_dict.get("last_pick_time", "")
            )
            
            # Parse Draft Order
            order_rows = batch_data.get("Draft_Order!A2:G100", [])
            draft_order = []
            current_pick_obj = None
            for row in order_rows:
                if len(row) >= 5:
                    try:
                        pick = DraftPick(
                            round=row[0],
                            pick=row[1],
                            team_id=row[2],
                            owner_name=row[3],
                            status=row[4],
                            player_id=row[5] if len(row) > 5 else 0,
                            player_name=row[6] if len(row) > 6 else ""
                        )
                        draft_order.append(pick)
                        if pick.is_current:
                            current_pick_obj = pick
                    except Exception as e:
                        logger.warning(f"Error parsing draft order row: {e}")
            
            # Build result
            result = {
                "league_meta": league_meta,
                "teams": teams,
                "requirements": requirements,
                "rosters": rosters_by_team,
                "available_players": available_players,
                "draft_state": draft_state,
                "draft_order": draft_order,
                "current_pick": current_pick_obj
            }
            
            self._cache[cache_key] = result
            logger.info("Successfully fetched and parsed all draft data in ONE API call!")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching all draft data: {e}")
            # Return empty structure on error
            return {
                "league_meta": LeagueMeta("PlayoffPurge", "Week 18", "Unknown"),
                "teams": [],
                "requirements": {},
                "rosters": {},
                "available_players": [],
                "draft_state": DraftState(1, 1, False, False, ""),
                "draft_order": [],
                "current_pick": None
            }
    
    def _update_range(self, range_name: str, values: List[List]) -> bool:
        """
        Update a range in the spreadsheet.
        
        Args:
            range_name: Range to update (e.g., "Draft_State!B2")
            values: 2D list of values to write
            
        Returns:
            True if successful, False otherwise
        """
        try:
            service = self._build_service()
            self._rate_limit()
            
            body = {'values': values}
            result = service.spreadsheets().values().update(
                spreadsheetId=self.sheet_id,
                range=range_name,
                valueInputOption='RAW',
                body=body
            ).execute()
            
            logger.info(f"Updated {result.get('updatedCells', 0)} cells in {range_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating range {range_name}: {e}")
            return False
    
    def make_draft_pick(self, player_id: str, team_id: int, owner_name: str, current_week: str) -> bool:
        """
        Execute a draft pick: mark player as drafted, add to roster, update draft order.
        
        Args:
            player_id: ID of player being drafted (string to support FanDuel hyphenated IDs)
            team_id: ID of team making the pick
            owner_name: Name of owner making the pick
            current_week: Current week for roster entry
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # 1. Get current state
            draft_state = self.get_draft_state(use_cache=False)
            current_pick = self.get_current_pick(use_cache=False)
            
            if not current_pick:
                logger.error("No current pick found")
                return False
            
            # 2. Verify it's the right team's turn
            if current_pick.team_id != team_id or current_pick.owner_name != owner_name:
                logger.error(f"Not {owner_name}'s turn (current: {current_pick.owner_name})")
                return False
            
            # 3. Get player details
            all_players = self.get_available_players(use_cache=False)
            player = next((p for p in all_players if p.player_id == player_id), None)
            
            if not player or not player.is_available:
                logger.error(f"Player {player_id} not available")
                return False
            
            # 4. Mark player as drafted in Available_Players tab
            # Find the row number for this player by searching through all rows
            all_rows = self._get_range("Available_Players!A2:A500")
            player_row = None
            for idx, row in enumerate(all_rows):
                if len(row) > 0 and str(row[0]) == str(player_id):
                    player_row = idx + 2  # +2 for header and 0-index
                    break
            
            if player_row is None:
                logger.error(f"Could not find row for player_id {player_id}")
                return False
            
            if not self._update_range(f"Available_Players!F{player_row}", [["drafted"]]):
                return False
            
            # 5. Add player to Rosters tab (append new row)
            # Rosters structure: A:team_id, B:week, C:position, D:player_name, E:team, 
            #                    F:points, G:projected_points, H:status, I:roster_eligibility
            roster_values = [[
                team_id,                    # A: team_id
                current_week,               # B: week
                player.position,            # C: position
                player.player_name,         # D: player_name
                player.nfl_team,            # E: team (NFL team)
                0,                          # F: points (will be updated later)
                0,                          # G: projected_points (will be updated later)
                "active",                   # H: status
                player.roster_eligibility   # I: roster_eligibility
            ]]
            
            service = self._build_service()
            service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range="Rosters!A:I",
                valueInputOption='RAW',
                body={'values': roster_values}
            ).execute()
            
            # 6. Update Draft_Order tab for this pick
            draft_order = self.get_draft_order(use_cache=False)
            for idx, pick in enumerate(draft_order):
                if pick.is_current:
                    pick_row = idx + 2  # +2 for header and 0-index
                    self._update_range(
                        f"Draft_Order!E{pick_row}:G{pick_row}",
                        [["completed", player_id, player.player_name]]
                    )
                    
                    # Mark next pick as current if it exists
                    if idx + 1 < len(draft_order):
                        next_pick_row = idx + 3
                        self._update_range(f"Draft_Order!E{next_pick_row}", [["current"]])
                    break
            
            # 7. Update Draft_State tab
            next_pick = draft_state.current_pick + 1
            next_round = draft_state.current_round
            
            # Check if we need to advance to next round
            total_picks_per_round = len(set(p.team_id for p in draft_order if p.round == 1))
            if next_pick > total_picks_per_round:
                next_round += 1
                next_pick = 1
            
            from datetime import datetime
            self._update_range("Draft_State!B2:B5", [
                [str(next_round)],
                [str(next_pick)],
                ["true"],
                ["false" if next_round <= 5 else "true"],  # Assuming 5 rounds
                [datetime.now().isoformat()]
            ])
            
            # 8. Clear relevant caches
            self._cache.pop("available_players_all", None)
            self._cache.pop(f"available_players_{player.position}", None)
            self._cache.pop("draft_state", None)
            self._cache.pop("draft_order", None)
            self._cache.pop(f"roster_{team_id}", None)
            
            logger.info(f"Successfully drafted {player.player_name} for {owner_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error making draft pick: {e}")
            return False
    
    def drop_player(self, team_id: int, player_name: str, current_week: str) -> bool:
        """
        Drop a player from a team's roster.
        
        Args:
            team_id: ID of team dropping the player
            player_name: Name of player to drop
            current_week: Current week
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Find the player in Rosters tab
            all_rows = self._get_range("Rosters!A2:H500")
            player_row = None
            player_id = None
            
            for idx, row in enumerate(all_rows):
                if len(row) >= 4:
                    row_team_id = int(row[0]) if row[0] else 0
                    row_week = row[1].strip() if len(row) > 1 else ""
                    row_player_name = row[3].strip() if len(row) > 3 else ""
                    
                    if (row_team_id == team_id and 
                        row_week.lower() == current_week.lower() and 
                        row_player_name == player_name):
                        player_row = idx + 2  # +2 for header and 0-index
                        # Try to find player_id from Available_Players
                        break
            
            if player_row is None:
                logger.error(f"Could not find player {player_name} for team {team_id}")
                return False
            
            # Delete the row from Rosters
            service = self._build_service()
            service.spreadsheets().batchUpdate(
                spreadsheetId=self.sheet_id,
                body={
                    "requests": [{
                        "deleteDimension": {
                            "range": {
                                "sheetId": self._get_sheet_id("Rosters"),
                                "dimension": "ROWS",
                                "startIndex": player_row - 1,
                                "endIndex": player_row
                            }
                        }
                    }]
                }
            ).execute()
            
            # Mark player as available in Available_Players (if exists)
            available_rows = self._get_range("Available_Players!A2:F500")
            for idx, row in enumerate(available_rows):
                if len(row) >= 2 and row[1].strip() == player_name:
                    available_row = idx + 2
                    self._update_range(f"Available_Players!F{available_row}", [["available"]])
                    break
            
            # Clear relevant caches
            self._cache.pop(f"roster_{team_id}", None)
            self._cache.pop("available_players_all", None)
            
            logger.info(f"Successfully dropped {player_name} from team {team_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error dropping player: {e}")
            return False
    
    def add_player(self, team_id: int, player_id: str, current_week: str) -> bool:
        """
        Add a player to a team's roster (from free agency).
        
        Args:
            team_id: ID of team adding the player
            player_id: ID of player to add
            current_week: Current week
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get player details from Available_Players
            all_players = self.get_available_players(use_cache=False)
            player = next((p for p in all_players if p.player_id == player_id), None)
            
            if not player or not player.is_available:
                logger.error(f"Player {player_id} not available")
                return False
            
            # Add player to Rosters tab (append new row) including roster_eligibility
            roster_values = [[
                team_id,
                current_week,
                player.position,
                player.player_name,
                player.nfl_team,
                0,  # points (will be updated later)
                0,  # projected_points (will be updated later)
                "active",
                player.roster_eligibility  # roster_eligibility from Available_Players
            ]]
            
            service = self._build_service()
            service.spreadsheets().values().append(
                spreadsheetId=self.sheet_id,
                range="Rosters!A:I",
                valueInputOption='RAW',
                body={'values': roster_values}
            ).execute()
            
            # Mark player as drafted in Available_Players tab
            all_rows = self._get_range("Available_Players!A2:A500")
            player_row = None
            for idx, row in enumerate(all_rows):
                if len(row) > 0 and str(row[0]) == str(player_id):
                    player_row = idx + 2  # +2 for header and 0-index
                    break
            
            if player_row:
                self._update_range(f"Available_Players!F{player_row}", [["drafted"]])
            
            # Clear relevant caches
            self._cache.pop(f"roster_{team_id}", None)
            self._cache.pop("available_players_all", None)
            
            logger.info(f"Successfully added {player.player_name} to team {team_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding player: {e}")
            return False
    
    def _get_sheet_id(self, sheet_name: str) -> int:
        """Get the sheet ID for a given sheet name."""
        try:
            service = self._build_service()
            spreadsheet = service.spreadsheets().get(spreadsheetId=self.sheet_id).execute()
            
            for sheet in spreadsheet.get('sheets', []):
                if sheet['properties']['title'] == sheet_name:
                    return sheet['properties']['sheetId']
            
            logger.error(f"Sheet '{sheet_name}' not found")
            return 0
            
        except Exception as e:
            logger.error(f"Error getting sheet ID: {e}")
            return 0
    
    def refresh_cache(self):
        """Clear cache to force fresh data fetch."""
        self._cache.clear()
        logger.info("Cache cleared")


# Global instance
sheets_client = SheetsClient()
