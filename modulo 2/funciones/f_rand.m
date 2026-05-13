function [seed]=f_rand;

%In general, you can generate N random numbers in the interval (a,b) with the formula r = a + (b-a).*rand(N,1).

a=[10001,99999]; 
r=a(1)+(a(2)-a(1))*rand; 
r=round(r);

if mod(r,2)==0;r=r+1;end 


%seed=197034863/27127
seed=197034863;
seed=num2str(seed); 
r=num2str(r);

seed=[seed,r]; 
seed=str2double(seed); 
end 