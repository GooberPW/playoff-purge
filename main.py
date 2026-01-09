"""FastAPI application for PlayoffPurge fantasy football dashboard."""
import logging
import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config import settings
from sheets_client import sheets_client
from fanduel_client import fanduel_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="PlayoffPurge Dashboard",
    description="Fantasy Football Playoff League Dashboard",
    version="1.0.0"
)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# HTTP Basic Auth for admin endpoints
security = HTTPBasic()


def validate_roster_with_flex(roster_players: list, required_positions: list) -> tuple[bool, str]:
    """
    Validate roster with FLEX eligibility support.
    
    Uses a greedy matching algorithm:
    1. Fill exact position matches first (QB → QB, RB → RB, etc.)
    2. Fill FLEX slots with remaining FLEX-eligible players
    3. Ensure all required positions are filled
    
    Args:
        roster_players: List of Player objects with roster_eligibility
        required_positions: List of position strings (e.g., ["QB", "RB", "WR", "FLEX", "FLEX", "FLEX"])
        
    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    from collections import Counter
    from models import Player
    
    # Convert to lists for manipulation
    required = required_positions.copy()
    players = roster_players.copy()
    
    # Track which players have been assigned
    assigned_players = set()
    unfilled_positions = []
    
    # Phase 1: Fill exact non-FLEX matches first
    for pos in required[:]:
        if pos.upper() == "FLEX":
            continue
            
        # Find a player that can fill this exact position
        for player in players:
            if player in assigned_players:
                continue
                
            # Check if player can fill this specific position
            if player.can_fill_position(pos):
                assigned_players.add(player)
                required.remove(pos)
                break
        else:
            # No player found for this position
            unfilled_positions.append(pos)
    
    # Phase 2: Fill FLEX slots with remaining FLEX-eligible players
    flex_slots = [pos for pos in required if pos.upper() == "FLEX"]
    
    for flex_slot in flex_slots:
        # Find any unassigned FLEX-eligible player
        for player in players:
            if player in assigned_players:
                continue
                
            if player.can_fill_position("FLEX"):
                assigned_players.add(player)
                required.remove(flex_slot)
                break
        else:
            # No FLEX-eligible player available
            unfilled_positions.append("FLEX")
    
    # Check if all positions filled
    if unfilled_positions:
        return False, f"Cannot fill required positions: {', '.join(unfilled_positions)}"
    
    # Check if we have exactly the right number of players
    if len(assigned_players) != len(roster_players):
        extra_players = len(roster_players) - len(assigned_players)
        return False, f"Roster has {extra_players} extra player(s) that don't fit requirements"
    
    return True, "Roster valid"


def verify_admin(credentials: Annotated[HTTPBasicCredentials, Depends(security)]):
    """Verify admin credentials for protected endpoints."""
    is_correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"), b"admin"
    )
    is_correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"), settings.admin_password.encode("utf8")
    )
    
    if not (is_correct_username and is_correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """
    Main dashboard page showing all teams and standings.
    Sorted by projected points (descending).
    """
    try:
        # Fetch data from Google Sheets
        league_meta = sheets_client.get_league_meta(use_cache=True)
        teams = sheets_client.get_teams_with_rosters(use_cache=True)
        
        # Sort teams by projected points (highest first)
        teams.sort(key=lambda t: t.total_projected_points, reverse=True)
        
        # Update seeds based on projection ranking
        for idx, team in enumerate(teams, start=1):
            team.seed = idx
        
        # Separate teams by status for better UI
        active_teams = [t for t in teams if t.is_active]
        eliminated_teams = [t for t in teams if t.is_eliminated]
        champions = [t for t in teams if t.is_champion]
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "league_meta": league_meta,
                "teams": teams,
                "active_teams": active_teams,
                "eliminated_teams": eliminated_teams,
                "champions": champions,
                "app_title": settings.app_title,
            }
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load dashboard. Please check your configuration."
        )


@app.post("/refresh")
async def refresh_data(username: Annotated[str, Depends(verify_admin)]):
    """
    Admin endpoint to manually refresh the cache.
    Requires HTTP Basic Auth (username: admin, password: from env var).
    """
    try:
        sheets_client.refresh_cache()
        logger.info(f"Cache refreshed by {username}")
        return {
            "status": "success",
            "message": "Cache cleared. Next request will fetch fresh data."
        }
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    Health check endpoint for deployment monitoring.
    """
    try:
        # Try to fetch league meta to verify Sheets API is working
        meta = sheets_client.get_league_meta(use_cache=True)
        return {
            "status": "healthy",
            "league": meta.league_name,
            "week": meta.current_week
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@app.get("/draft", response_class=HTMLResponse)
async def draft_page(request: Request):
    """
    Draft page showing weekly roster requirements and draft summary.
    """
    try:
        # Fetch data from Google Sheets
        league_meta = sheets_client.get_league_meta(use_cache=True)
        teams = sheets_client.get_teams(use_cache=True)
        
        # Get roster requirement for current week
        roster_requirement = sheets_client.get_roster_requirement_for_week(
            league_meta.current_week, 
            use_cache=True
        )
        
        # Get drafted rosters for current week
        drafted_rosters = sheets_client.get_rosters_by_week(
            league_meta.current_week,
            use_cache=True
        )
        
        # Compute draft counts per team
        draft_counts = {
            team.team_id: len(drafted_rosters.get(team.team_id, []))
            for team in teams
        }
        
        return templates.TemplateResponse(
            "draft.html",
            {
                "request": request,
                "league_meta": league_meta,
                "teams": teams,
                "roster_requirement": roster_requirement,
                "drafted_rosters": drafted_rosters,
                "draft_counts": draft_counts,
                "app_title": settings.app_title,
            }
        )
    except Exception as e:
        logger.error(f"Error loading draft page: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to load draft page. Please check your configuration."
        )


@app.get("/api/teams")
async def get_teams_api():
    """
    Optional API endpoint to get teams data as JSON.
    Useful for debugging or future integrations.
    """
    try:
        teams = sheets_client.get_teams(use_cache=True)
        return {
            "teams": [
                {
                    "team_id": t.team_id,
                    "owner_name": t.owner_name,
                    "team_name": t.team_name,
                    "seed": t.seed,
                    "status": t.status,
                    "total_points": t.total_points,
                    "current_week": t.current_week
                }
                for t in teams
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching teams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/draft/state")
async def get_draft_state_api():
    """Get current draft state with available players and current pick."""
    try:
        draft_state = sheets_client.get_draft_state(use_cache=False)
        current_pick = sheets_client.get_current_pick(use_cache=False)
        available_players = sheets_client.get_available_players(use_cache=False)
        teams = sheets_client.get_teams(use_cache=True)
        league_meta = sheets_client.get_league_meta(use_cache=True)
        roster_requirement = sheets_client.get_roster_requirement_for_week(
            league_meta.current_week,
            use_cache=True
        )
        
        # Get drafted rosters for current week
        drafted_rosters = sheets_client.get_rosters_by_week(
            league_meta.current_week,
            use_cache=False
        )
        
        return {
            "draft_state": {
                "current_round": draft_state.current_round,
                "current_pick": draft_state.current_pick,
                "draft_started": draft_state.draft_started,
                "draft_complete": draft_state.draft_complete,
                "last_pick_time": draft_state.last_pick_time
            },
            "current_pick": {
                "round": current_pick.round,
                "pick": current_pick.pick,
                "team_id": current_pick.team_id,
                "owner_name": current_pick.owner_name,
                "status": current_pick.status
            } if current_pick else None,
            "roster_requirement": {
                "week": roster_requirement.week,
                "teams_left": roster_requirement.teams_left,
                "positions_required": roster_requirement.positions_required,
                "payout": roster_requirement.payout
            } if roster_requirement else None,
            "available_players": [
                {
                    "player_id": p.player_id,
                    "player_name": p.player_name,
                    "position": p.position,
                    "nfl_team": p.nfl_team,
                    "bye_week": p.bye_week,
                    "is_available": p.is_available,
                    "fppg": p.fppg,
                    "opponent": p.opponent
                }
                for p in available_players if p.is_available
            ],
            "teams": [
                {
                    "team_id": t.team_id,
                    "owner_name": t.owner_name,
                    "team_name": t.team_name,
                    "players_drafted": len(drafted_rosters.get(t.team_id, []))
                }
                for t in teams
            ],
            "drafted_rosters": {
                str(team_id): [
                    {
                        "position": p.position,
                        "player_name": p.player_name,
                        "team": p.team,
                        "points": p.points
                    }
                    for p in players
                ]
                for team_id, players in drafted_rosters.items()
            }
        }
    except Exception as e:
        logger.error(f"Error fetching draft state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/draft/pick")
async def make_draft_pick_api(request: Request):
    """
    Make a draft pick.
    
    Request body:
    {
        "owner_name": "Goober",
        "player_id": "124949-103020"  # Can be string (FanDuel) or int
    }
    """
    try:
        data = await request.json()
        owner_name = data.get("owner_name")
        player_id = data.get("player_id")
        
        # Convert player_id to string to support FanDuel hyphenated IDs
        if player_id is not None:
            player_id = str(player_id)
        
        if not owner_name or not player_id:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required fields: owner_name={owner_name}, player_id={player_id}"
            )
        
        # Get team_id for owner
        teams = sheets_client.get_teams(use_cache=False)
        team = next((t for t in teams if t.owner_name == owner_name), None)
        
        if not team:
            raise HTTPException(status_code=404, detail=f"Team not found for owner: {owner_name}")
        
        # Get current week
        league_meta = sheets_client.get_league_meta(use_cache=False)
        
        # Validate position requirements
        roster_requirement = sheets_client.get_roster_requirement_for_week(
            league_meta.current_week,
            use_cache=False
        )
        
        if roster_requirement:
            # Get team's current roster for this week
            drafted_rosters = sheets_client.get_rosters_by_week(
                league_meta.current_week,
                use_cache=False
            )
            team_roster = drafted_rosters.get(team.team_id, [])
            
            # Get player being drafted
            available_players = sheets_client.get_available_players(use_cache=False)
            player = next((p for p in available_players if p.player_id == player_id), None)
            
            if player:
                # Simulate adding this player to roster
                from models import Player
                simulated_player = Player(
                    position=player.position,
                    player_name=player.player_name,
                    team=player.nfl_team,
                    points=0,
                    projected_points=0,
                    roster_eligibility=player.roster_eligibility,
                    status="active"
                )
                
                simulated_roster = team_roster + [simulated_player]
                
                # Parse requirements
                required_positions = [p.strip() for p in roster_requirement.positions_required.split(',')]
                
                # Validate with FLEX support
                is_valid, error_msg = validate_roster_with_flex(simulated_roster, required_positions)
                
                if not is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot add player: {error_msg}"
                    )
        
        # Make the pick
        success = sheets_client.make_draft_pick(
            player_id=player_id,
            team_id=team.team_id,
            owner_name=owner_name,
            current_week=league_meta.current_week
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Successfully drafted player {player_id}",
                "owner": owner_name
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to make draft pick")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error making draft pick: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/player/{player_id}")
async def get_player_details(player_id: str):
    """
    Get enhanced player details from FanDuel API.
    
    Args:
        player_id: FanDuel player ID (e.g., "124949-103020")
        
    Returns:
        Enhanced player data with projections, images, etc.
    """
    try:
        # Fetch from FanDuel API
        player_data = await fanduel_client.get_player_data(player_id)
        
        if player_data:
            return {
                "status": "success",
                "player_id": player_id,
                "data": player_data
            }
        else:
            # Return minimal data if FanDuel fetch fails
            return {
                "status": "partial",
                "player_id": player_id,
                "data": {
                    "image_url": fanduel_client.get_player_image_url(player_id),
                    "projection": None,
                    "opponent": None,
                    "injury_status": None,
                    "expert_analysis": []
                }
            }
    except Exception as e:
        logger.error(f"Error fetching player details for {player_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/draft")
async def get_draft_api():
    """
    API endpoint to get draft data as JSON.
    Useful for debugging or future integrations.
    """
    try:
        league_meta = sheets_client.get_league_meta(use_cache=True)
        teams = sheets_client.get_teams(use_cache=True)
        roster_requirement = sheets_client.get_roster_requirement_for_week(
            league_meta.current_week,
            use_cache=True
        )
        drafted_rosters = sheets_client.get_rosters_by_week(
            league_meta.current_week,
            use_cache=True
        )
        
        return {
            "league_meta": {
                "league_name": league_meta.league_name,
                "current_week": league_meta.current_week,
                "last_updated": league_meta.last_updated
            },
            "roster_requirement": {
                "week": roster_requirement.week,
                "teams_left": roster_requirement.teams_left,
                "positions_required": roster_requirement.positions_required,
                "payout": roster_requirement.payout
            } if roster_requirement else None,
            "teams": [
                {
                    "team_id": t.team_id,
                    "owner_name": t.owner_name,
                    "team_name": t.team_name,
                    "seed": t.seed,
                    "status": t.status,
                    "players_drafted": len(drafted_rosters.get(t.team_id, []))
                }
                for t in teams
            ],
            "drafted_players": {
                str(team_id): [
                    {
                        "position": p.position,
                        "player_name": p.player_name,
                        "team": p.team,
                        "points": p.points,
                        "status": p.status
                    }
                    for p in players
                ]
                for team_id, players in drafted_rosters.items()
            }
        }
    except Exception as e:
        logger.error(f"Error fetching draft data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fa/drop")
async def drop_player_api(request: Request):
    """
    Drop a player from a team's roster (Free Agency).
    
    Request body:
    {
        "owner_name": "Goober",
        "player_name": "Patrick Mahomes"
    }
    """
    try:
        data = await request.json()
        owner_name = data.get("owner_name")
        player_name = data.get("player_name")
        
        if not owner_name or not player_name:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: owner_name and player_name"
            )
        
        # Get team_id for owner
        teams = sheets_client.get_teams(use_cache=False)
        team = next((t for t in teams if t.owner_name == owner_name), None)
        
        if not team:
            raise HTTPException(status_code=404, detail=f"Team not found for owner: {owner_name}")
        
        # Get current week
        league_meta = sheets_client.get_league_meta(use_cache=False)
        
        # Drop the player
        success = sheets_client.drop_player(
            team_id=team.team_id,
            player_name=player_name,
            current_week=league_meta.current_week
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Successfully dropped {player_name}",
                "owner": owner_name
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to drop player")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error dropping player: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/fa/add")
async def add_player_api(request: Request):
    """
    Add a player to a team's roster (Free Agency).
    
    Request body:
    {
        "owner_name": "Goober",
        "player_id": "124949-103020"
    }
    """
    try:
        data = await request.json()
        owner_name = data.get("owner_name")
        player_id = data.get("player_id")
        
        # Convert player_id to string
        if player_id is not None:
            player_id = str(player_id)
        
        if not owner_name or not player_id:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: owner_name and player_id"
            )
        
        # Get team_id for owner
        teams = sheets_client.get_teams(use_cache=False)
        team = next((t for t in teams if t.owner_name == owner_name), None)
        
        if not team:
            raise HTTPException(status_code=404, detail=f"Team not found for owner: {owner_name}")
        
        # Get current week
        league_meta = sheets_client.get_league_meta(use_cache=False)
        
        # Validate position requirements
        roster_requirement = sheets_client.get_roster_requirement_for_week(
            league_meta.current_week,
            use_cache=False
        )
        
        if roster_requirement:
            # Get team's current roster for this week
            drafted_rosters = sheets_client.get_rosters_by_week(
                league_meta.current_week,
                use_cache=False
            )
            team_roster = drafted_rosters.get(team.team_id, [])
            
            # Get player being added
            available_players = sheets_client.get_available_players(use_cache=False)
            player = next((p for p in available_players if p.player_id == player_id), None)
            
            if player:
                # Simulate adding this player to roster
                from models import Player
                simulated_player = Player(
                    position=player.position,
                    player_name=player.player_name,
                    team=player.nfl_team,
                    points=0,
                    projected_points=0,
                    roster_eligibility=player.roster_eligibility,
                    status="active"
                )
                
                simulated_roster = team_roster + [simulated_player]
                
                # Parse requirements
                required_positions = [p.strip() for p in roster_requirement.positions_required.split(',')]
                
                # Validate with FLEX support
                is_valid, error_msg = validate_roster_with_flex(simulated_roster, required_positions)
                
                if not is_valid:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot add player: {error_msg}"
                    )
        
        # Add the player
        success = sheets_client.add_player(
            team_id=team.team_id,
            player_id=player_id,
            current_week=league_meta.current_week
        )
        
        if success:
            return {
                "status": "success",
                "message": f"Successfully added player {player_id}",
                "owner": owner_name
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to add player")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding player: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
