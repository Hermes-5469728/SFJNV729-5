"""
Frontend Layer - Streamlit UI (交互界面颗粒)
OpenCode Hooks:
  /ui show crcl              # 显示CrCl计算器
  /ui show notes             # 显示寄生笔记
  /ui show anchors           # 显示锚点系统
  /ui hide <component>       # 隐藏指定组件
  /ui reload <component>     # 重载组件数据
"""

import streamlit as st
import requests
import json
from loguru import logger
from datetime import datetime

class CrClCalculator:
    """CrCl预填计算器组件"""
    
    @staticmethod
    def render():
        """渲染CrCl计算器"""
        st.subheader("🧪 CrCl 预填计算器")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            age = st.number_input("年龄 (岁)", min_value=1, max_value=120, value=30, key="crcl_age")
        
        with col2:
            weight = st.number_input("体重 (kg)", min_value=1, max_value=300, value=70, key="crcl_weight")
        
        with col3:
            scr = st.number_input("血清肌酐 (mg/dL)", min_value=0.1, max_value=10.0, value=1.0, step=0.1, key="crcl_scr")
        
        gender = st.radio("性别", ["male", "female"], index=0, horizontal=True, key="crcl_gender")
        
        if st.button("计算 CrCl", key="crcl_calc_btn"):
            if gender == "male":
                crcl = ((140 - age) * weight) / (72 * scr)
            else:
                crcl = ((140 - age) * weight) / (72 * scr) * 0.85
            
            st.success(f"估算肌酐清除率 (CrCl): **{crcl:.1f} mL/min**")
            
            if "parasite_notes" not in st.session_state:
                st.session_state.parasite_notes = []
            
            st.session_state.parasite_notes.append({
                "title": f"CrCl计算结果: {crcl:.1f} mL/min",
                "content": f"年龄: {age}, 体重: {weight}kg, Scr: {scr}mg/dL",
                "category": "医疗记录",
                "priority": "中",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

class ParasiteNotes:
    """寄生笔记组件"""
    
    @staticmethod
    def render():
        """渲染寄生笔记"""
        st.subheader("📝 寄生笔记")
        
        if "parasite_notes" not in st.session_state:
            st.session_state.parasite_notes = []
        
        new_title = st.text_input("笔记标题", key="note_title")
        new_content = st.text_area("笔记内容", key="note_content")
        
        col1, col2 = st.columns(2)
        with col1:
            category = st.selectbox("分类", ["医疗记录", "用药记录", "检查报告", "其他"], key="note_cat")
        with col2:
            priority = st.selectbox("优先级", ["高", "中", "低"], key="note_prio")
        
        if st.button("添加笔记", key="add_note_btn"):
            if new_title and new_content:
                st.session_state.parasite_notes.append({
                    "title": new_title,
                    "content": new_content,
                    "category": category,
                    "priority": priority,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                st.success("笔记已添加")
            else:
                st.warning("请填写标题和内容")
        
        if st.session_state.parasite_notes:
            st.divider()
            st.write(f"共 {len(st.session_state.parasite_notes)} 条笔记")
            
            for i, note in enumerate(st.session_state.parasite_notes):
                with st.expander(f"{note['title']} ({note['category']})"):
                    st.write(note['content'])
                    st.caption(f"时间: {note['timestamp']} | 优先级: {note['priority']}")
                    
                    if st.button(f"删除", key=f"del_note_{i}"):
                        st.session_state.parasite_notes.pop(i)
                        st.experimental_rerun()

class AnchorSystem:
    """锚点系统组件"""
    
    @staticmethod
    def render():
        """渲染锚点系统"""
        st.subheader("⚓ 锚点系统")
        
        if "anchors" not in st.session_state:
            st.session_state.anchors = []
        
        anchor_name = st.text_input("锚点名称", key="anchor_name")
        anchor_target = st.text_input("锚点目标 (URL或ID)", key="anchor_target")
        anchor_desc = st.text_input("锚点描述", key="anchor_desc")
        
        if st.button("添加锚点", key="add_anchor_btn"):
            if anchor_name and anchor_target:
                st.session_state.anchors.append({
                    "name": anchor_name,
                    "target": anchor_target,
                    "description": anchor_desc
                })
                st.success("锚点已添加")
            else:
                st.warning("请填写名称和目标")
        
        if st.session_state.anchors:
            st.divider()
            st.write(f"共 {len(st.session_state.anchors)} 个锚点")
            
            for i, anchor in enumerate(st.session_state.anchors):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{anchor['name']}**")
                    st.write(f"目标: {anchor['target']}")
                    if anchor['description']:
                        st.caption(anchor['description'])
                with col2:
                    if st.button(f"跳转", key=f"goto_anchor_{i}"):
                        st.markdown(f"[跳转到锚点]({anchor['target']})")

def run():
    """运行前端界面"""
    st.set_page_config(
        page_title="个人数据处理中心",
        page_icon="🧬",
        layout="wide"
    )
    
    st.title("🧬 个人数据处理中心")
    
    with st.sidebar:
        st.header("导航")
        st.page_link("app.py", label="主页", icon="🏠")
        
        st.divider()
        st.header("系统状态")
        st.write("API状态: 🔴 未连接")
        
        st.divider()
        st.header("快速链接")
        if "anchors" in st.session_state:
            for anchor in st.session_state.anchors[:3]:
                st.write(f"- {anchor['name']}")
    
    tab1, tab2, tab3, tab4 = st.tabs(["对话中心", "CrCl计算器", "寄生笔记", "锚点系统"])
    
    with tab1:
        st.subheader("💬 对话中心")
        st.info("对话功能开发中...")
    
    with tab2:
        CrClCalculator.render()
    
    with tab3:
        ParasiteNotes.render()
    
    with tab4:
        AnchorSystem.render()

if __name__ == "__main__":
    run()