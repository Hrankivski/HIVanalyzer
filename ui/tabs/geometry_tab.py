import streamlit as st
from ui import designer

def render(room_l, room_w, room_l_cut, room_w_cut):
    fig = designer.render_blueprint(
        room_l, room_w, room_l_cut, room_w_cut, st.session_state.elements_df
    )
    st.plotly_chart(fig, width="stretch")

    st.subheader("Таблиця елементів (Швидке редагування)")
    st.write(
        "Тут ви можете вручну змінювати координати, розміри та потужність об'єктів."
    )
    if not st.session_state.elements_df.empty:
        st.session_state.elements_df = st.data_editor(
            st.session_state.elements_df, num_rows="dynamic", use_container_width=True
        )
    else:
        st.info("Додайте елементи за допомогою кнопок у боковій панелі ліворуч.")
