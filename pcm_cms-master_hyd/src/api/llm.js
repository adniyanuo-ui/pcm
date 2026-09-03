import api from "@/api/index";
import axios from "axios";

export function on_get_llm_data(params) {
    return api.get(`/api/cms/llm/revise/`, {"params": params});
}

export function star(data) {
    return api({
        method: 'POST',
        url: "/api/cms/llm/revise/",
        data: data,
    })
}

export function show_llm_chat(params) {
    return api.get(`/api/cms/llm/show/chat/`, {"params": params});
}

export function show_llm_chat_one(id) {
    return api.get(`/api/cms/llm/show/chat/${id}/`)
}