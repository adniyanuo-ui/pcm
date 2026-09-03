import api from "@/api/index";
import axios from "axios";

export function on_delete(did, params) {
    return api.delete(`/api/cms/system/qr/${did}/`, {"params": params});
}

export function on_add_qr(data) {
    return api({
        method: 'POST',
        url: "/api/cms/system/qr/",
        data: data,
    })
}

export function on_get_qr(params) {
    return api.get(`/api/cms/system/qr/`, {"params": params});
}
