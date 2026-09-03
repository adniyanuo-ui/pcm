import api from "@/api/index";

export function on_get_data(params) {
    return api.get(`/api/cms/patient/patient/`, {"params": params});
}

export function on_token() {
    return api.post(`/api/cms/speech/token/`);
}

export function on_asp(data) {
    return api.post(`/api/cms/speech/speech/`, data);
}
