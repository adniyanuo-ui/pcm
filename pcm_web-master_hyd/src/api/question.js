import request from '@/utils/request';

export function on_get_question(this_id) {
    return request({
        url: `/api/question/question/${this_id}/`,
        method: 'get',
    });
}

export function on_get_op(params) {
    return request({
        url: `/api/question/op/`,
        method: 'get',
        params: params
    });
}

export function on_get_answer(params) {
    return request({
        url: `/api/patient/answer/`,
        method: 'get',
        params: params
    });
}

export function on_submit_answer(data) {
    return request({
        url: `/api/patient/answer/`,
        method: 'post',
        data: data
    });
}


export function get_result() {
    return request({
        url: '/api/patient/result/',
        method: 'post',
    });
}
