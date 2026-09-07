"""病机—治法—治疗原型—核心方—历史全库的单路径检索。"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path

from .gold import GoldFormulaSet, TreatmentPrototype, TreatmentPrototypeCatalog
from .retriever import FormulaRetriever, RetrievalQuery
from .text import normalize_text, phrase_similarity, unique_phrases


_MEANING_LINE = re.compile(r"^(方论(?:选录)?|方解|方义|方剂解|方药解)[:：]\s*(.+)$")


def _items(value) -> tuple[str, ...]:
    if value in (None, ""):
        return ()
    values = [value] if isinstance(value, str) else value
    if not isinstance(values, (list, tuple)):
        raise ValueError("临床辨证字段必须是字符串或字符串数组")
    return tuple(unique_phrases(values))


@dataclass(frozen=True)
class ClinicalFormulaProfile:
    etiology: tuple[str, ...] = ()
    location: tuple[str, ...] = ()
    nature: tuple[str, ...] = ()
    trend: tuple[str, ...] = ()
    primary_pathogenesis: tuple[str, ...] = ()
    secondary_pathogenesis: tuple[str, ...] = ()
    concurrent_pathogenesis: tuple[str, ...] = ()
    primary_treatment: tuple[str, ...] = ()
    secondary_treatment: tuple[str, ...] = ()
    adjunct_treatment: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, data: dict | None) -> "ClinicalFormulaProfile":
        data = data or {}
        return cls(**{name: _items(data.get(name)) for name in cls.__dataclass_fields__})

    @classmethod
    def from_query(cls, query: RetrievalQuery) -> "ClinicalFormulaProfile":
        return cls(
            primary_pathogenesis=tuple(unique_phrases([*query.mechanisms, *query.syndromes])),
            primary_treatment=tuple(unique_phrases(query.treatments)),
        )

    @property
    def pathogenesis(self) -> tuple[str, ...]:
        return tuple(
            unique_phrases(
                [
                    *self.primary_pathogenesis,
                    *self.secondary_pathogenesis,
                    *self.concurrent_pathogenesis,
                ]
            )
        )

    @property
    def treatments(self) -> tuple[str, ...]:
        return tuple(
            unique_phrases(
                [
                    *self.primary_treatment,
                    *self.secondary_treatment,
                    *self.adjunct_treatment,
                ]
            )
        )

    def as_dict(self) -> dict:
        return {name: list(getattr(self, name)) for name in self.__dataclass_fields__}


def _coverage(terms: tuple[str, ...], text: str) -> tuple[float, list[str], list[str]]:
    if not terms:
        return 1.0, [], []
    matched, missing, scores = [], [], []
    for term in terms:
        score = phrase_similarity(term, text)
        scores.append(score)
        (matched if score >= 0.5 else missing).append(term)
    return sum(scores) / len(scores), matched, missing


def _weighted_coverage(groups: list[tuple[tuple[str, ...], float]], text: str):
    active = [(terms, weight) for terms, weight in groups if terms]
    if not active:
        return 1.0, [], []
    total_weight = sum(weight for _, weight in active)
    score, matched, missing = 0.0, [], []
    for terms, weight in active:
        coverage, group_matched, group_missing = _coverage(terms, text)
        score += coverage * weight
        matched.extend(group_matched)
        missing.extend(group_missing)
    return score / total_weight, matched, missing


def _weighted_ontology_coverage(
    groups: list[tuple[tuple[str, ...], float]], prototypes: list[TreatmentPrototype]
):
    """用受控治疗原型补足辞典功用的同义表达，不跨原型泛化。"""
    active = [(terms, weight) for terms, weight in groups if terms]
    if not active:
        return 1.0, [], []
    ontology_terms = [term for prototype in prototypes for term in prototype.treatment_terms]
    total_weight = sum(weight for _, weight in active)
    score, matched, missing = 0.0, [], []
    for terms, weight in active:
        term_scores = [
            max((phrase_similarity(term, candidate) for candidate in ontology_terms), default=0.0)
            for term in terms
        ]
        score += (sum(term_scores) / len(term_scores)) * weight
        for term, term_score in zip(terms, term_scores):
            (matched if term_score >= 0.5 else missing).append(term)
    return score / total_weight, matched, missing


class LayeredFormulaRetriever:
    """面向试用的默认检索器；历史全库只在核心方不足时调用。"""

    def __init__(
        self,
        index_path: Path,
        prototype_path: Path,
        gold_path: Path,
        gold_metadata_path: Path,
    ):
        self.retriever = FormulaRetriever(index_path)
        self.catalog = TreatmentPrototypeCatalog(prototype_path)
        self.gold = GoldFormulaSet(gold_path, gold_metadata_path, self.catalog)

    def metadata(self) -> dict:
        index = self.retriever.metadata()
        return {
            **index,
            "layered_ready": self.gold.compatible_with(index),
            "treatment_prototypes": len(self.catalog.prototypes),
            "gold_formulas": len(self.gold.records),
            "level2_status": "not_built",
        }

    def _route(self, profile: ClinicalFormulaProfile) -> list[dict]:
        treatment_text = "；".join(profile.treatments)
        mechanism_text = "；".join(
            unique_phrases(
                [
                    *profile.pathogenesis,
                    *profile.etiology,
                    *profile.location,
                    *profile.nature,
                    *profile.trend,
                ]
            )
        )
        routed = []
        for prototype in self.catalog.prototypes:
            treatment_hits = [
                term
                for term in prototype.treatment_terms
                if phrase_similarity(term, treatment_text) >= 0.65
            ]
            mechanism_hits = [
                term
                for term in prototype.mechanism_terms
                if phrase_similarity(term, mechanism_text) >= 0.65
            ]
            # 同义治法词只贡献一次最高分，避免“益气/补气”等同义词重复堆分；
            # 同时奖励能够覆盖多个已确认治法的复合治疗结构。
            treatment_score = max(
                (
                    phrase_similarity(term, treatment_text) * min(14, len(term) * 2)
                    for term in treatment_hits
                ),
                default=0.0,
            )
            covered_treatments = [
                value
                for value in profile.treatments
                if max(
                    (phrase_similarity(value, term) for term in prototype.treatment_terms),
                    default=0.0,
                )
                >= 0.5
            ]
            treatment_score += len(covered_treatments) * 3
            mechanism_score = max(
                (
                    phrase_similarity(term, mechanism_text) * min(8, len(term) + 2)
                    for term in mechanism_hits
                ),
                default=0.0,
            )
            score = treatment_score + mechanism_score
            if score:
                routed.append(
                    {
                        "id": prototype.id,
                        "name": prototype.name,
                        "parent_formulas": list(prototype.parent_formulas),
                        "matched_treatments": treatment_hits,
                        "matched_pathogenesis": mechanism_hits,
                        "_score": score,
                    }
                )
        routed.sort(key=lambda item: (-item["_score"], item["id"]))
        result = routed[:3]
        for item in result:
            item.pop("_score", None)
        return result

    @staticmethod
    def _meaning_evidence(candidate: dict) -> str:
        other = candidate.get("fields", {}).get("正文及其他", "")
        for line in other.splitlines():
            match = _MEANING_LINE.match(line.strip())
            if match:
                text = match.group(2).strip()
                return text if len(text) <= 1000 else text[:1000].rstrip() + "……"
        return ""

    @staticmethod
    def _profile_direction_conflicts(
        profile: ClinicalFormulaProfile, routed: list[dict], catalog: TreatmentPrototypeCatalog
    ) -> list[str]:
        nature = normalize_text("；".join([*profile.nature, *profile.pathogenesis]))
        cold = "寒" in nature and "热" not in nature
        heat = "热" in nature and "寒" not in nature
        directions = {catalog.by_id[item["id"]].direction for item in routed}
        conflicts: list[str] = []
        if cold and "cooling" in directions:
            conflicts.append("当前病性偏寒，但已确认治法路由到清凉治疗原型")
        if heat and "warming" in directions:
            conflicts.append("当前病性偏热，但已确认治法路由到温热治疗原型")
        return conflicts

    @staticmethod
    def _potential_conflicts(
        profile: ClinicalFormulaProfile,
        prototypes: list[TreatmentPrototype],
        actual_treatment: str,
    ) -> list[str]:
        nature = normalize_text("；".join([*profile.nature, *profile.pathogenesis]))
        cold = "寒" in nature and "热" not in nature
        heat = "热" in nature and "寒" not in nature
        directions = {prototype.direction for prototype in prototypes}
        action = normalize_text(actual_treatment)
        warming = "warming" in directions or any(
            marker in action
            for marker in ("温中", "温阳", "回阳", "助阳", "补阳", "散寒", "祛寒")
        )
        cooling = "cooling" in directions or any(
            marker in action
            for marker in ("清热", "泻火", "凉血", "清营", "清暑", "退热")
        )
        conflicts = []
        if cold and cooling and not warming:
            conflicts.append("当前资料偏寒，候选方实际治法偏清凉，方向可能冲突")
        if heat and warming and not cooling:
            conflicts.append("当前资料偏热，候选方实际治法偏温热，方向可能冲突")
        return conflicts

    def _annotate(
        self,
        candidate: dict,
        profile: ClinicalFormulaProfile,
        query: RetrievalQuery,
        routed: list[dict],
        layer: str,
        gold_record: dict | None = None,
        rank: int = 0,
    ) -> dict:
        fields = candidate.get("fields") or {}
        if gold_record:
            all_prototype_ids = list(gold_record.get("prototype_ids") or [])
            supported_prototype_ids = [
                evidence["prototype_id"]
                for evidence in gold_record.get("classification_evidence") or []
                if evidence.get("parent_formula_match")
                or evidence.get("treatment_terms_in_dictionary_actions")
            ]
        else:
            classified = self.catalog.classify(
                candidate.get("name", ""), fields.get("功用", ""), fields.get("主治", "")
            )
            all_prototype_ids = [item["id"] for item in classified]
            supported_prototype_ids = [
                item["id"]
                for item in classified
                if item["parent_hit"] or item["treatment_hits"]
            ]
        prototype_ids = supported_prototype_ids or all_prototype_ids
        primary = self.catalog.by_id.get(prototype_ids[0]) if prototype_ids else None
        candidate_prototypes = [self.catalog.by_id[item] for item in prototype_ids]
        routed_ids = {item["id"] for item in routed}

        treatment_groups = (
            [
                (profile.primary_treatment, 0.6),
                (profile.secondary_treatment, 0.25),
                (profile.adjunct_treatment, 0.15),
            ]
            if profile.treatments
            else [(profile.treatments, 1.0)]
        )
        treatment_coverage, matched_treatment, missing_treatment = _weighted_coverage(
            treatment_groups, fields.get("功用", "")
        )
        routed_candidate_prototypes = [
            self.catalog.by_id[prototype_id]
            for prototype_id in prototype_ids
            if prototype_id in routed_ids
        ]
        ontology_coverage, ontology_matched, _ = _weighted_ontology_coverage(
            treatment_groups, routed_candidate_prototypes
        )
        # 只对该候选实际功用/代表方已经支持、且本次路由命中的治疗原型做同义归并。
        # 不能因为候选碰巧命中任一宽泛方族，就把所有未覆盖治法一并视作已覆盖。
        treatment_coverage = max(treatment_coverage, ontology_coverage)
        ontology_supported = bool(ontology_matched)
        pathogenesis_coverage, matched_pathogenesis, missing_pathogenesis = _weighted_coverage(
            [
                (profile.primary_pathogenesis, 0.65),
                (profile.secondary_pathogenesis, 0.2),
                (profile.concurrent_pathogenesis, 0.15),
            ]
            if profile.pathogenesis
            else [(profile.pathogenesis, 1.0)],
            "；".join([fields.get("主治", ""), fields.get("功用", "")]),
        )
        clinical_terms = tuple(
            unique_phrases(
                [
                    *query.symptoms,
                    *query.syndromes,
                    *query.tongue,
                    *query.pulse,
                    *query.complexion,
                    *query.voice,
                ]
            )
        )
        clinical_coverage, matched_clinical, _ = _coverage(
            clinical_terms, fields.get("主治", "")
        )
        missing_facts = [
            label
            for label in ("方源", "组成", "功用", "主治")
            if not fields.get(label, "").strip()
        ]
        conflicts = self._potential_conflicts(
            profile, candidate_prototypes, fields.get("功用", "")
        )
        aggressive_unrouted = [
            self.catalog.by_id[prototype_id].name
            for prototype_id in prototype_ids
            if prototype_id not in routed_ids
            and self.catalog.by_id[prototype_id].strategy == "attacking"
        ]
        cautions = []
        ontology_matched_set = set(ontology_matched)
        ontology_supported_missing = [
            term for term in missing_treatment if term in ontology_matched_set
        ]
        unsupported_treatment = [
            term for term in missing_treatment if term not in ontology_matched_set
        ]
        if ontology_supported_missing:
            cautions.append(
                "辞典功用与已确认治法用语不同，已按同一治疗原型归并："
                + "、".join(ontology_supported_missing)
            )
        if unsupported_treatment:
            cautions.append(
                "辞典功用未充分覆盖已确认主治法：" + "、".join(unsupported_treatment)
            )
        if missing_pathogenesis and pathogenesis_coverage < 0.2 and clinical_coverage < 0.35:
            cautions.append("辞典主治未充分覆盖已确认主病机：" + "、".join(missing_pathogenesis))
        if missing_facts:
            cautions.append("辞典本条缺少：" + "、".join(missing_facts))
        cautions.extend(conflicts)
        if aggressive_unrouted:
            cautions.append(
                "候选方还包含当前治法未覆盖的攻下结构：" + "、".join(aggressive_unrouted)
            )
        if candidate.get("quality_flags"):
            cautions.append("辞典条目带质量标记：" + "、".join(candidate["quality_flags"]))

        source_complete = not missing_facts and not candidate.get("quality_flags")
        path_supported = pathogenesis_coverage >= 0.2 or clinical_coverage >= 0.35
        if (
            source_complete
            and treatment_coverage >= 0.5
            and path_supported
            and not conflicts
            and not aggressive_unrouted
        ):
            consistency = "较高"
        elif source_complete and treatment_coverage >= 0.3 and not conflicts:
            consistency = "需复核"
        else:
            consistency = "不足"

        base = (100 if layer == "core" else 82) - rank * 2
        score = (
            base
            + treatment_coverage * 28
            + pathogenesis_coverage * 14
            + clinical_coverage * 12
            - len(conflicts) * 45
            - len(missing_facts) * 12
            - bool(candidate.get("quality_flags")) * 16
            - len(aggressive_unrouted) * 28
        )
        family = None
        if primary:
            family = {
                "id": primary.id,
                "name": primary.name,
                "parent_formulas": list(primary.parent_formulas),
                "review_status": (
                    gold_record.get("review_status")
                    if gold_record
                    else "runtime_dictionary_classification"
                ),
            }
        candidate = dict(candidate)
        candidate.update(
            selection_layer=layer,
            treatment_family=family,
            reverse_validation={
                "consistency": consistency,
                "composition_source": (
                    "《中医方剂大辞典》组成原文"
                    if fields.get("组成")
                    else "辞典本条未提供组成"
                ),
                "formula_meaning": self._meaning_evidence(candidate),
                "actual_treatment": fields.get("功用", ""),
                "actual_indications": fields.get("主治", ""),
                "matched_treatment": matched_treatment,
                "matched_pathogenesis": matched_pathogenesis,
                "matched_clinical_evidence": matched_clinical,
                "treatment_ontology_supported": ontology_supported,
                "unmatched_treatment_structures": aggressive_unrouted,
                "cautions": cautions or ["未发现明确方向冲突，仍须医师结合完整四诊复核"],
                "facts_inferred_by_model": False,
            },
            _selection_score=score,
        )
        return candidate

    @staticmethod
    def _finalize(candidates: list[dict], top_k: int) -> list[dict]:
        candidates.sort(key=lambda item: (-item["_selection_score"], item["id"]))
        selected, seen_names = [], set()
        for candidate in candidates:
            name = normalize_text(candidate["name"])
            if name in seen_names:
                continue
            candidate.pop("_selection_score", None)
            selected.append(candidate)
            seen_names.add(name)
            if len(selected) == top_k:
                break
        return selected

    def search(
        self,
        query: RetrievalQuery | dict,
        *,
        clinical_profile: ClinicalFormulaProfile | dict | None = None,
        full_fields: bool = False,
    ) -> dict:
        if isinstance(query, dict):
            query = RetrievalQuery.from_mapping(query)
        profile = (
            clinical_profile
            if isinstance(clinical_profile, ClinicalFormulaProfile)
            else ClinicalFormulaProfile.from_mapping(clinical_profile)
            if clinical_profile is not None
            else ClinicalFormulaProfile.from_query(query)
        )
        routed = self._route(profile)
        profile_conflicts = self._profile_direction_conflicts(profile, routed, self.catalog)
        index_metadata = self.retriever.metadata()
        gold_ready = self.gold.compatible_with(index_metadata)
        if profile_conflicts:
            return {
                "query": query.as_dict(),
                "clinical_profile": profile.as_dict(),
                "candidates": [],
                "retrieval": {
                    "candidate_pool": 0,
                    "returned": 0,
                    "reverse_validation_rejected": 0,
                    "validation_status": "clinical_profile_conflict",
                    "profile_conflicts": profile_conflicts,
                    "treatment_prototypes": routed,
                    "gold_size": len(self.gold.records),
                    "gold_ready": gold_ready,
                    "search_path": ["治疗原型/方族"],
                    "stopped_at": "clinical_profile",
                    "fallback_used": False,
                    "fallback_reason": "病性与已确认治法方向冲突，须先由医师修订",
                    "score_note": "病性与治法方向冲突时不检索基础方；最终由医师修订确认。",
                },
            }
        core_candidates: list[dict] = []
        core_pool = 0

        if gold_ready and routed:
            route_ids = {item["id"] for item in routed}
            records = self.gold.records_for_prototypes(route_ids)
            core_pool = len(records)
            route_position = {item["id"]: index for index, item in enumerate(routed)}
            boosts, reasons = {}, {}
            for record in records:
                overlap = route_ids.intersection(record.get("prototype_ids") or [])
                best = min(route_position[item] for item in overlap)
                matched_parent_names = {
                    normalize_text(parent)
                    for route in routed
                    if route["id"] in overlap
                    for parent in route["parent_formulas"]
                }
                parent_boost = 18.0 if normalize_text(record["name"]) in matched_parent_names else 0.0
                official_boost = (
                    5.0 if record.get("selection_source") == "official_catalog_candidate" else 0.0
                )
                boosts[record["id"]] = 42.0 - best * 8.0 + parent_boost + official_boost
                reasons[record["id"]] = [
                    "治疗原型命中："
                    + "、".join(self.catalog.by_id[item].name for item in overlap)
                ]
                if parent_boost:
                    reasons[record["id"]].append("该方为命中治疗原型的代表方")
            subset = self.retriever.search_subset(
                query,
                [record["id"] for record in records],
                boosts=boosts,
                routes=reasons,
                full_fields=full_fields,
                top_k=min(20, max(query.top_k * 3, 12)),
            )
            core_candidates = [
                self._annotate(
                    candidate,
                    profile,
                    query,
                    routed,
                    "core",
                    self.gold.by_id[candidate["id"]],
                    rank,
                )
                for rank, candidate in enumerate(subset["candidates"])
            ]

        core_ranked = sorted(core_candidates, key=lambda item: -item["_selection_score"])
        core_sufficient = bool(
            core_ranked
            and core_ranked[0]["reverse_validation"]["consistency"] == "较高"
        )
        fallback_reason = ""
        archive_pool = 0
        combined = list(core_candidates)
        if not core_sufficient:
            if not gold_ready:
                fallback_reason = "核心方清单缺失或与当前辞典索引版本不一致"
            elif not routed:
                fallback_reason = "已确认治法与病机尚不能稳定路由到治疗原型"
            elif not core_candidates:
                fallback_reason = "对应治疗原型下暂无满足资料门禁的核心方"
            else:
                fallback_reason = "核心候选的治法/病机反向验证不足或存在方向冲突"
            archive_query = replace(query, top_k=min(20, max(query.top_k * 3, 12)))
            archive = self.retriever.search(archive_query, full_fields=full_fields)
            archive_pool = archive["retrieval"]["candidate_pool"]
            combined.extend(
                self._annotate(
                    candidate,
                    profile,
                    query,
                    routed,
                    "archive",
                    self.gold.by_id.get(candidate["id"]),
                    rank,
                )
                for rank, candidate in enumerate(archive["candidates"])
            )

        # 反向核验不是仅供展示的标签：方向冲突、事实链缺失或治法覆盖不足的
        # 条目不能继续进入医生可带入的基础方列表。允许“需复核”供医生判断，
        # 但“不足”直接淘汰；若全部淘汰，上层会提示补充四诊或修订治法。
        eligible = [
            candidate
            for candidate in combined
            if candidate["reverse_validation"]["consistency"] != "不足"
        ]
        rejected_count = len(combined) - len(eligible)
        candidates = self._finalize(eligible, query.top_k)
        return {
            "query": query.as_dict(),
            "clinical_profile": profile.as_dict(),
            "candidates": candidates,
            "retrieval": {
                "candidate_pool": core_pool + archive_pool,
                "returned": len(candidates),
                "reverse_validation_rejected": rejected_count,
                "validation_status": (
                    "consistent_candidates_found"
                    if candidates
                    else "no_consistent_candidate"
                ),
                "treatment_prototypes": routed,
                "gold_size": len(self.gold.records),
                "gold_ready": gold_ready,
                "search_path": ["治疗原型/方族", "核心经典方"]
                + (["9.6万历史全库"] if not core_sufficient else []),
                "stopped_at": "core" if core_sufficient else "archive",
                "fallback_used": not core_sufficient,
                "fallback_reason": fallback_reason,
                "score_note": "排序分与一致性只用于候选筛选，不代表临床有效率；最终由医师确认。",
            },
        }
