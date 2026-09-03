import request from '@/utils/request';

export function on_add_patient(data) {
    return request({
        url: '/api/patient/patient/',
        method: 'post',
        data: data
    });
}


export function on_submit(data) {
    return request({
        url: '/api/patient/patient/',
        method: 'post',
        data: data
    });
}

export function on_submit_medical_record(data) {
  return request({
    url: '/api/llm/medical/record/',
    method: 'post',
    data: data
  });
}
