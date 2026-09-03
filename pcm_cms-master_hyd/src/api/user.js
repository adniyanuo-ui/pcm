import api from "@/api/index";
import axios from "axios";

export function on_get_user(params) {
    return api.get(`/api/cms/user/user/`, {"params": params});
}