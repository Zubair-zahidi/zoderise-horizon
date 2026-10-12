"""Editable, curriculum-neutral starting points for school workflows."""
import streamlit as st

TASKS = {
    "Lesson plan": "Create a lesson plan with measurable learning objectives, a warm-up, teaching steps, guided practice, independent practice, differentiation, materials, and a short exit ticket. Include a realistic timing breakdown.",
    "Assessment & rubric": "Create an assessment with a mix of question types, difficulty levels, point values, a separate answer key, and a marking rubric. Check that points add up. Avoid ambiguous questions.",
    "Socratic tutor": "Tutor me through this topic. Start by checking my current understanding with one question. Give hints before solutions and ask one question at a time. Adapt to my answers.",
    "Revision roadmap": "Create a practical revision plan with short study sessions, active recall, spaced review, worked examples, and checkpoints. Explain how to adjust the plan when a topic is difficult.",
    "Explain & practise": "Explain the central idea simply, give a worked example, then three practice problems of increasing difficulty. Put solutions in a separate section. Use clean LaTeX for mathematics.",
    "Parent communication": "Draft a respectful message to a parent or guardian about this topic. Use clear language, concrete next steps, and a collaborative tone. Use placeholders for personal details; do not invent student records.",
}


def build_classroom_prompt(task: str, topic: str, level: str, language: str, minutes: int, requirements: str) -> str:
    if task not in TASKS:
        raise ValueError("Choose a supported classroom task.")
    if not topic.strip():
        raise ValueError("Add a topic before creating your prompt.")
    return (
        f"{TASKS[task]}\n\nTopic: {topic.strip()}\nLearner level: {level}\n"
        f"Language: {language}\nAvailable time: {minutes} minutes\n"
        f"Additional requirements: {requirements.strip() or 'None specified.'}\n\n"
        "If a curriculum or source is not supplied, make that clear instead of claiming alignment. "
        "Keep the material appropriate for the learner level."
    )


def render_classroom_studio() -> None:
    st.subheader("A better starting point")
    st.caption("Build an editable brief for a lesson, assessment, or study session. Review it before asking your local AI.")
    with st.form("classroom_brief"):
        task = st.selectbox("What are you working on?", list(TASKS))
        topic = st.text_input("Topic", placeholder="For example: fractions, grade 6")
        c1, c2, c3 = st.columns(3)
        with c1:
            level = st.selectbox("Learner level", ["Primary school", "Middle school", "High school", "University", "Adult / professional"])
        with c2:
            language = st.selectbox("Output language", ["English", "Dari", "Pashto", "Arabic", "French", "Chinese"])
        with c3:
            minutes = st.number_input("Time available (minutes)", min_value=5, max_value=240, value=40, step=5)
        requirements = st.text_area("Context and requirements", placeholder="Learning goals, prior knowledge, materials, or accessibility needs")
        if st.form_submit_button("Build my brief", type="primary"):
            try:
                st.session_state["classroom_draft"] = build_classroom_prompt(task, topic, level, language, int(minutes), requirements)
            except ValueError as exc:
                st.error(str(exc))
    if st.session_state.get("classroom_draft"):
        draft = st.text_area("Review and edit your brief", key="classroom_draft", height=240)
        with st.container(horizontal=True):
            if st.button("Continue in chat", icon=":material/arrow_forward:", type="primary", disabled=not draft.strip()):
                st.session_state["pending_chat_draft"] = draft
                st.session_state.page = "Chat"
                st.rerun()
            st.download_button("Download brief", draft, file_name="classroom-brief.md", mime="text/markdown")
