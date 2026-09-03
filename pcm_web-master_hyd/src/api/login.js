import request from '@/utils/request';

export function on_login(data) {
  return request({
    url: '/api/patient/login/',
    method: 'post',
    data: data
  });
}

