function [BED] = f_BED(D,I1,p_radiobiologicos,lamda,index,cell)

alfa_beta=p_radiobiologicos.liver.alfa_beta; %alfa/beta Gy 
mu=p_radiobiologicos.liver.mu; 

s=size(I1);

BED=zeros(s);

%% liver 
organo=index.liver; 

ind=I1==organo;

G=(lamda)./((alfa_beta)*(lamda+mu));
BED(ind)=D(ind)+G.*D(ind).^2; 
%% pretumor 
organo=index.pretumor; 

ind=I1==organo;

G=(lamda)./((alfa_beta)*(lamda+mu));
BED(ind)=D(ind)+G.*D(ind).^2; 

%% tumor 
alfa_beta=p_radiobiologicos.tumor.alfa_beta; %alfa/beta Gy 
mu=p_radiobiologicos.tumor.mu; 

G=(lamda)./((alfa_beta)*(lamda+mu));

for i=1:length(cell)
    if cell(i)>=index.tumor
       ind=I1==cell(i);
       
       BED(ind)=D(ind)+G.*D(ind).^2;
    end 
end 

end

