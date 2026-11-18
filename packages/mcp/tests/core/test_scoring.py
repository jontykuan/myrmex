from packages.mcp.src.core.scoring import score_field


def test_scores_active_attractive_pheromone() -> None:
    pheromones = [
        {
            "target_ref": "slice-1",
            "kind": "test_red",
            "intensity": 10.0,
            "decay_rate": 0.0,
            "updated_at": 1000,
            "expires_at": None,
            "payload": None,
        }
    ]
    candidates = score_field(pheromones, leased_targets=set(), now=1100, block_threshold=5.0)
    assert len(candidates) == 1
    assert candidates[0]["target_ref"] == "slice-1"
    assert candidates[0]["net_score"] == 10.0
    assert candidates[0]["dominant_kind"] == "test_red"


def test_excludes_expired_pheromone_at_exact_expiry() -> None:
    pheromones = [
        {
            "target_ref": "slice-1",
            "kind": "task_seed",
            "intensity": 10.0,
            "decay_rate": 0.01,
            "updated_at": 1000,
            "expires_at": 1050,
            "payload": None,
        }
    ]
    assert score_field(pheromones, leased_targets=set(), now=1050, block_threshold=5.0) == []


def test_excludes_blocked_target_at_threshold_and_subtracts_repulsion() -> None:
    pheromones = [
        {
            "target_ref": "slice-1",
            "kind": "task_seed",
            "intensity": 10.0,
            "decay_rate": 0.0,
            "updated_at": 1000,
            "expires_at": None,
            "payload": None,
        },
        {
            "target_ref": "slice-1",
            "kind": "blocked_unknown",
            "intensity": 5.0,
            "decay_rate": 0.0,
            "updated_at": 1000,
            "expires_at": None,
            "payload": None,
        },
        {
            "target_ref": "slice-2",
            "kind": "task_seed",
            "intensity": 10.0,
            "decay_rate": 0.0,
            "updated_at": 1000,
            "expires_at": None,
            "payload": None,
        },
        {
            "target_ref": "slice-2",
            "kind": "conflict_hotspot",
            "intensity": 3.0,
            "decay_rate": 0.0,
            "updated_at": 1000,
            "expires_at": None,
            "payload": None,
        },
    ]
    candidates = score_field(pheromones, leased_targets=set(), now=1000, block_threshold=5.0)
    assert [c["target_ref"] for c in candidates] == ["slice-2"]
    assert candidates[0]["net_score"] == 7.0
