"""
review_explorer.py — what Salt City Coffee's customers are saying, at a glance.

The owner reads every review on the shop's website, but thirty reviews across
three locations is more than anyone can hold in their head. This page shows
what customers praise and complain about — by location and by subject — and
answers plain-English questions like "Do people like the mocha latte?" or "What
is the most popular product?" from the reviews themselves, with the evidence
underneath.

The page is assembly again: `analyze_reviews` does all the API work (from the
cache after the first run), and the Q&A box is three calls you have already
written — find the question's scope and evidence, build the messages, ask the
model.

Run it:  Run and Debug -> "Streamlit Run: Current File"
Test it: pytest tests/test_pipeline.py -k app
"""
import os
import streamlit as st
from reviews import (
    REVIEWS_FILE,
    analyze_reviews,
    answer_question,
    ask_llm,
    build_messages,
    describe_scope,
    load_aliases,
    summarize_items,
)
reviews_file = os.environ.get("REVIEWS_FILE", REVIEWS_FILE)
st.title("Salt City Coffee — What Customers Are Saying")
st.markdown("Every customer review, broken into the things people talk about. "
            "Filter by location or subject, or ask a question at the bottom of "
            "the page.")

mentions = analyze_reviews(reviews_file)

left, right = st.columns(2)
with left:
    location = st.selectbox("Location",
                            ["All"] + sorted(mentions["location"].unique()),
                            key="location")
with right:
    subject = st.selectbox("Subject",
                           ["All"] + sorted(mentions["subject"].unique()),
                           key="subject")

selected = mentions
if location != "All":
    selected = selected[selected["location"] == location]
if subject != "All":
    selected = selected[selected["subject"] == subject]

col1, col2, col3, col4 = st.columns(4)
col1.metric("Reviews", selected["review_id"].nunique())
col2.metric("Mentions", len(selected))
col3.metric("Positive", int((selected["mention_sentiment"] == "positive").sum()))
col4.metric("Negative", int((selected["mention_sentiment"] == "negative").sum()))

summary = summarize_items(selected)
praised_tab, complained_tab, said_tab = st.tabs(
    ["Most praised", "Most complained about", "What people said"])
praised = summary[summary["net"] > 0].sort_values("net", ascending=False).head(5)
praised_tab.dataframe(praised, hide_index=True)
complained = summary[summary["net"] < 0].sort_values("net").head(5)
complained_tab.dataframe(complained, hide_index=True)
said_tab.dataframe(
    selected[["date", "location", "item", "subject", "mention_sentiment",
              "assessments", "sentence_text"]],
    hide_index=True)

st.subheader("Ask the reviews")
question = st.text_input("Your question", key="question",
                         placeholder="What is the most popular product?")
if st.button("Ask", key="ask") and question.strip():
    scope, evidence = answer_question(question, mentions, load_aliases())
    if evidence.empty:
        st.warning(f"No reviews mention {describe_scope(scope)}. Try a menu item, "
                   "a staff member, or part of the shop.")
    else:
        messages = build_messages(question, evidence)
        with st.spinner("Asking the model..."):
            answer = ask_llm(messages)
        st.markdown(answer)
        st.caption(f"Based on {len(evidence)} mentions — {describe_scope(scope)}:")
        st.dataframe(
            evidence[["date", "location", "item", "mention_sentiment",
                      "sentence_text"]],
            hide_index=True)
