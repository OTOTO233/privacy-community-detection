"""API routers for the deployable backend framework."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, UploadFile

from .ea_schema import EAOptimizeRequest
from .services import IntegratedPMCDMBackend

framework = IntegratedPMCDMBackend()

system_router = APIRouter()
pipeline_router = APIRouter()


@system_router.get("/")
async def root():
    return {
        "message": "Privacy Community Detection API",
        "framework": framework.framework_overview(),
    }


@system_router.get("/datasets")
async def dataset_catalog():
    return framework.dataset_catalog()


@system_router.get("/framework/architecture")
async def framework_architecture():
    return framework.framework_overview()


@system_router.post("/optimize/ea")
@system_router.post("/api/optimize/ea")
async def evolutionary_optimize(body: EAOptimizeRequest):
    """遗传算法搜索隐私–效用相关参数（ε、λ 等），返回最优个体与逐代历史。

    同时注册 ``/optimize/ea`` 与 ``/api/optimize/ea``：前者配合 devServer 去掉 /api 前缀的代理；
    后者供直接访问 8000 端口且路径带 ``/api`` 的部署方式使用。
    """
    return framework.run_evolutionary_optimize(body)


def _request_form(
    source_type: str,
    dataset_name: str,
    algorithm: str,
    epsilon: float,
    delta: float,
    key_size: int,
    random_state: int,
    lambd: float,
    include_benchmark: Optional[str] = None,
    layout: Optional[str] = None,
    **extras,
):
    payload = {
        "source_type": source_type,
        "dataset_name": dataset_name,
        "algorithm": algorithm,
        "epsilon": epsilon,
        "delta": delta,
        "key_size": key_size,
        "random_state": random_state,
        "lambd": lambd,
    }
    if include_benchmark is not None:
        payload["include_benchmark"] = include_benchmark
    if layout is not None:
        payload["layout"] = layout
    payload.update(extras)
    return payload


@pipeline_router.post("/detect")
async def detect_communities(
    source_type: str = Form("builtin"),
    dataset_name: str = Form("karate"),
    algorithm: str = Form("DH-Louvain"),
    epsilon: float = Form(1.0),
    delta: float = Form(1e-5),
    key_size: int = Form(512),
    random_state: int = Form(42),
    lambd: float = Form(0.5),
    include_benchmark: str = Form("true"),
    lfr_preset: str = Form("bench500"),
    lfr_custom_enabled: str = Form("false"),
    lfr_n: Optional[str] = Form(None),
    lfr_tau1: Optional[str] = Form(None),
    lfr_tau2: Optional[str] = Form(None),
    lfr_mu: Optional[str] = Form(None),
    lfr_average_degree: Optional[str] = Form(None),
    lfr_max_degree: Optional[str] = Form(None),
    lfr_min_community: Optional[str] = Form(None),
    lfr_max_community: Optional[str] = Form(None),
    lfr_max_iters: Optional[str] = Form(None),
    lfr_multiplex_layers: Optional[str] = Form(None),
    mlfr_network_type: Optional[str] = Form("UU"),
    mlfr_n: Optional[str] = Form(None),
    mlfr_avg: Optional[str] = Form(None),
    mlfr_max: Optional[str] = Form(None),
    mlfr_mix: Optional[str] = Form(None),
    mlfr_tau1: Optional[str] = Form(None),
    mlfr_tau2: Optional[str] = Form(None),
    mlfr_mincom: Optional[str] = Form(None),
    mlfr_maxcom: Optional[str] = Form(None),
    mlfr_l: Optional[str] = Form(None),
    mlfr_dc: Optional[str] = Form(None),
    mlfr_rc: Optional[str] = Form(None),
    mlfr_mparam1: Optional[str] = Form(None),
    mlfr_on: Optional[str] = Form(None),
    mlfr_om: Optional[str] = Form(None),
    biogrid_member: Optional[str] = Form(None),
    biogrid_top_layers: Optional[str] = Form(None),
    biogrid_min_edges: Optional[str] = Form(None),
    biogrid_max_nodes: Optional[str] = Form(None),
    biogrid_include_genetic: Optional[str] = Form("true"),
    biogrid_auto_layers: Optional[str] = Form("true"),
    file: Optional[UploadFile] = File(None),
):
    form = _request_form(
        source_type,
        dataset_name,
        algorithm,
        epsilon,
        delta,
        key_size,
        random_state,
        lambd,
        include_benchmark=include_benchmark,
        lfr_preset=lfr_preset,
        lfr_custom_enabled=lfr_custom_enabled,
        lfr_n=lfr_n,
        lfr_tau1=lfr_tau1,
        lfr_tau2=lfr_tau2,
        lfr_mu=lfr_mu,
        lfr_average_degree=lfr_average_degree,
        lfr_max_degree=lfr_max_degree,
        lfr_min_community=lfr_min_community,
        lfr_max_community=lfr_max_community,
        lfr_max_iters=lfr_max_iters,
        lfr_multiplex_layers=lfr_multiplex_layers,
        mlfr_network_type=mlfr_network_type,
        mlfr_n=mlfr_n,
        mlfr_avg=mlfr_avg,
        mlfr_max=mlfr_max,
        mlfr_mix=mlfr_mix,
        mlfr_tau1=mlfr_tau1,
        mlfr_tau2=mlfr_tau2,
        mlfr_mincom=mlfr_mincom,
        mlfr_maxcom=mlfr_maxcom,
        mlfr_l=mlfr_l,
        mlfr_dc=mlfr_dc,
        mlfr_rc=mlfr_rc,
        mlfr_mparam1=mlfr_mparam1,
        mlfr_on=mlfr_on,
        mlfr_om=mlfr_om,
        biogrid_member=biogrid_member,
        biogrid_top_layers=biogrid_top_layers,
        biogrid_min_edges=biogrid_min_edges,
        biogrid_max_nodes=biogrid_max_nodes,
        biogrid_include_genetic=biogrid_include_genetic,
        biogrid_auto_layers=biogrid_auto_layers,
    )
    bundle = framework.load_bundle_from_request(
        source_type=source_type,
        dataset_name=dataset_name,
        file=file,
        random_state=random_state,
        form=form,
    )
    return framework.detect(bundle=bundle, form=form)


@pipeline_router.post("/visualize")
async def visualize_results(
    source_type: str = Form("builtin"),
    dataset_name: str = Form("karate"),
    algorithm: str = Form("DH-Louvain"),
    epsilon: float = Form(1.0),
    delta: float = Form(1e-5),
    key_size: int = Form(512),
    random_state: int = Form(42),
    lambd: float = Form(0.5),
    layout: str = Form("spring"),
    lfr_preset: str = Form("bench500"),
    lfr_custom_enabled: str = Form("false"),
    lfr_n: Optional[str] = Form(None),
    lfr_tau1: Optional[str] = Form(None),
    lfr_tau2: Optional[str] = Form(None),
    lfr_mu: Optional[str] = Form(None),
    lfr_average_degree: Optional[str] = Form(None),
    lfr_max_degree: Optional[str] = Form(None),
    lfr_min_community: Optional[str] = Form(None),
    lfr_max_community: Optional[str] = Form(None),
    lfr_max_iters: Optional[str] = Form(None),
    lfr_multiplex_layers: Optional[str] = Form(None),
    mlfr_network_type: Optional[str] = Form("UU"),
    mlfr_n: Optional[str] = Form(None),
    mlfr_avg: Optional[str] = Form(None),
    mlfr_max: Optional[str] = Form(None),
    mlfr_mix: Optional[str] = Form(None),
    mlfr_tau1: Optional[str] = Form(None),
    mlfr_tau2: Optional[str] = Form(None),
    mlfr_mincom: Optional[str] = Form(None),
    mlfr_maxcom: Optional[str] = Form(None),
    mlfr_l: Optional[str] = Form(None),
    mlfr_dc: Optional[str] = Form(None),
    mlfr_rc: Optional[str] = Form(None),
    mlfr_mparam1: Optional[str] = Form(None),
    mlfr_on: Optional[str] = Form(None),
    mlfr_om: Optional[str] = Form(None),
    biogrid_member: Optional[str] = Form(None),
    biogrid_top_layers: Optional[str] = Form(None),
    biogrid_min_edges: Optional[str] = Form(None),
    biogrid_max_nodes: Optional[str] = Form(None),
    biogrid_include_genetic: Optional[str] = Form("true"),
    biogrid_auto_layers: Optional[str] = Form("true"),
    file: Optional[UploadFile] = File(None),
):
    form = _request_form(
        source_type,
        dataset_name,
        algorithm,
        epsilon,
        delta,
        key_size,
        random_state,
        lambd,
        layout=layout,
        lfr_preset=lfr_preset,
        lfr_custom_enabled=lfr_custom_enabled,
        lfr_n=lfr_n,
        lfr_tau1=lfr_tau1,
        lfr_tau2=lfr_tau2,
        lfr_mu=lfr_mu,
        lfr_average_degree=lfr_average_degree,
        lfr_max_degree=lfr_max_degree,
        lfr_min_community=lfr_min_community,
        lfr_max_community=lfr_max_community,
        lfr_max_iters=lfr_max_iters,
        lfr_multiplex_layers=lfr_multiplex_layers,
        mlfr_network_type=mlfr_network_type,
        mlfr_n=mlfr_n,
        mlfr_avg=mlfr_avg,
        mlfr_max=mlfr_max,
        mlfr_mix=mlfr_mix,
        mlfr_tau1=mlfr_tau1,
        mlfr_tau2=mlfr_tau2,
        mlfr_mincom=mlfr_mincom,
        mlfr_maxcom=mlfr_maxcom,
        mlfr_l=mlfr_l,
        mlfr_dc=mlfr_dc,
        mlfr_rc=mlfr_rc,
        mlfr_mparam1=mlfr_mparam1,
        mlfr_on=mlfr_on,
        mlfr_om=mlfr_om,
        biogrid_member=biogrid_member,
        biogrid_top_layers=biogrid_top_layers,
        biogrid_min_edges=biogrid_min_edges,
        biogrid_max_nodes=biogrid_max_nodes,
        biogrid_include_genetic=biogrid_include_genetic,
        biogrid_auto_layers=biogrid_auto_layers,
    )
    bundle = framework.load_bundle_from_request(
        source_type=source_type,
        dataset_name=dataset_name,
        file=file,
        random_state=random_state,
        form=form,
    )
    return framework.visualize(bundle=bundle, form=form)


@pipeline_router.post("/visualize3d")
async def visualize_results_3d(
    source_type: str = Form("builtin"),
    dataset_name: str = Form("karate"),
    algorithm: str = Form("DH-Louvain"),
    epsilon: float = Form(1.0),
    delta: float = Form(1e-5),
    key_size: int = Form(512),
    random_state: int = Form(42),
    lambd: float = Form(0.5),
    lfr_preset: str = Form("bench500"),
    lfr_custom_enabled: str = Form("false"),
    lfr_n: Optional[str] = Form(None),
    lfr_tau1: Optional[str] = Form(None),
    lfr_tau2: Optional[str] = Form(None),
    lfr_mu: Optional[str] = Form(None),
    lfr_average_degree: Optional[str] = Form(None),
    lfr_max_degree: Optional[str] = Form(None),
    lfr_min_community: Optional[str] = Form(None),
    lfr_max_community: Optional[str] = Form(None),
    lfr_max_iters: Optional[str] = Form(None),
    lfr_multiplex_layers: Optional[str] = Form(None),
    mlfr_network_type: Optional[str] = Form("UU"),
    mlfr_n: Optional[str] = Form(None),
    mlfr_avg: Optional[str] = Form(None),
    mlfr_max: Optional[str] = Form(None),
    mlfr_mix: Optional[str] = Form(None),
    mlfr_tau1: Optional[str] = Form(None),
    mlfr_tau2: Optional[str] = Form(None),
    mlfr_mincom: Optional[str] = Form(None),
    mlfr_maxcom: Optional[str] = Form(None),
    mlfr_l: Optional[str] = Form(None),
    mlfr_dc: Optional[str] = Form(None),
    mlfr_rc: Optional[str] = Form(None),
    mlfr_mparam1: Optional[str] = Form(None),
    mlfr_on: Optional[str] = Form(None),
    mlfr_om: Optional[str] = Form(None),
    biogrid_member: Optional[str] = Form(None),
    biogrid_top_layers: Optional[str] = Form(None),
    biogrid_min_edges: Optional[str] = Form(None),
    biogrid_max_nodes: Optional[str] = Form(None),
    biogrid_include_genetic: Optional[str] = Form("true"),
    biogrid_auto_layers: Optional[str] = Form("true"),
    file: Optional[UploadFile] = File(None),
):
    form = _request_form(
        source_type,
        dataset_name,
        algorithm,
        epsilon,
        delta,
        key_size,
        random_state,
        lambd,
        lfr_preset=lfr_preset,
        lfr_custom_enabled=lfr_custom_enabled,
        lfr_n=lfr_n,
        lfr_tau1=lfr_tau1,
        lfr_tau2=lfr_tau2,
        lfr_mu=lfr_mu,
        lfr_average_degree=lfr_average_degree,
        lfr_max_degree=lfr_max_degree,
        lfr_min_community=lfr_min_community,
        lfr_max_community=lfr_max_community,
        lfr_max_iters=lfr_max_iters,
        lfr_multiplex_layers=lfr_multiplex_layers,
        mlfr_network_type=mlfr_network_type,
        mlfr_n=mlfr_n,
        mlfr_avg=mlfr_avg,
        mlfr_max=mlfr_max,
        mlfr_mix=mlfr_mix,
        mlfr_tau1=mlfr_tau1,
        mlfr_tau2=mlfr_tau2,
        mlfr_mincom=mlfr_mincom,
        mlfr_maxcom=mlfr_maxcom,
        mlfr_l=mlfr_l,
        mlfr_dc=mlfr_dc,
        mlfr_rc=mlfr_rc,
        mlfr_mparam1=mlfr_mparam1,
        mlfr_on=mlfr_on,
        mlfr_om=mlfr_om,
        biogrid_member=biogrid_member,
        biogrid_top_layers=biogrid_top_layers,
        biogrid_min_edges=biogrid_min_edges,
        biogrid_max_nodes=biogrid_max_nodes,
        biogrid_include_genetic=biogrid_include_genetic,
        biogrid_auto_layers=biogrid_auto_layers,
    )
    bundle = framework.load_bundle_from_request(
        source_type=source_type,
        dataset_name=dataset_name,
        file=file,
        random_state=random_state,
        form=form,
    )
    return framework.visualize3d(bundle=bundle, form=form)
